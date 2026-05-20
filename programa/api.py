#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import contextlib
import io
import re
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile


ROOT_DIR = Path(__file__).resolve().parents[1]
PROGRAM_DIR = ROOT_DIR / "programa"
if str(PROGRAM_DIR) not in sys.path:
    sys.path.insert(0, str(PROGRAM_DIR))

try:
    from .procesar_archivo import main as procesar_archivo_main
except ImportError:
    from procesar_archivo import main as procesar_archivo_main
try:
    from .generar_carga_shopify_csv import main as generar_csv_main
except ImportError:
    from generar_carga_shopify_csv import main as generar_csv_main


RAW_INPUT_DIR = ROOT_DIR / "raw_input"
ALLOWED_EXTENSIONS = {".csv", ".xml"}
TXT_EXTENSION = ".txt"

app = FastAPI(
    title="Onix Processing API",
    description="API para recibir archivos CSV o XML, guardarlos en raw_input y procesarlos",
    version="1.0.0",
)


def _safe_filename(filename: str) -> str:
    clean_name = Path(filename or "").name.strip()
    return clean_name or "archivo"


def _ensure_unique_path(file_name: str) -> Path:
    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_INPUT_DIR / file_name
    if base_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un archivo con ese nombre en raw_input: {base_path.name}",
        )

    return base_path


def _ensure_timestamped_path(file_name: str) -> Path:
    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_INPUT_DIR / file_name
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    candidate = RAW_INPUT_DIR / f"{stem}_{timestamp}{suffix}"

    counter = 1
    while candidate.exists():
        candidate = RAW_INPUT_DIR / f"{stem}_{timestamp}_{counter}{suffix}"
        counter += 1

    return candidate


def _detect_file_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv o .xml")
    return suffix.lstrip(".")


def _run_processing_with_capture(file_path: Path) -> dict[str, object]:
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = procesar_archivo_main([str(file_path)])

    output = buffer.getvalue()

    summary_patterns = {
        "total_read": r"- Total leidos:\s*(\d+)",
        "raw_inserted": r"- Registros insertados en raw:\s*(\d+)",
        "raw_updated": r"- Registros actualizados en raw:\s*(\d+)",
        "raw_unchanged": r"- Registros sin cambios:\s*(\d+)",
        "raw_skipped": r"- Registros saltados \(sin ISBN\):\s*(\d+)",
        "raw_errors": r"- Errores de inserción/actualización:\s*(\d+)",
        "metadato_inserted": r"- Registros insertados en metadato:\s*(\d+)",
        "metadato_updated": r"- Registros actualizados en metadato:\s*(\d+)",
        "metadato_unchanged": r"- Registros sin cambios:\s*(\d+)",
        "metadato_skipped": r"- Registros saltados \(sin ISBN\):\s*(\d+)",
    }

    summary: dict[str, int] = {}
    for key, pattern in summary_patterns.items():
        match = re.search(pattern, output)
        if match:
            summary[key] = int(match.group(1))

    return {
        "result": result,
        "summary": summary,
        "output": output,
    }


async def _save_upload_file(upload: UploadFile) -> Path:
    original_name = _safe_filename(upload.filename or "")
    destination = _ensure_unique_path(original_name)

    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    await upload.seek(0)

    with destination.open("wb") as output_file:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)

    await upload.close()
    return destination


def _run_generate_csv_with_capture(isbns_txt_path: Path, output_path: Path) -> dict[str, object]:
    buffer = io.StringIO()
    argv = [str(isbns_txt_path), "--output", str(output_path)]

    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = generar_csv_main(argv)

    output = buffer.getvalue()
    return {"result": result, "output": output, "output_path": str(output_path)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/enriquecerdb")
async def process_file(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre")

    saved_path = await _save_upload_file(file)
    file_type = _detect_file_type(saved_path)

    processing = await asyncio.to_thread(_run_processing_with_capture, saved_path)
    process_result = int(processing["result"])
    if process_result != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo {file_type.upper()}",
        )

    return {
        "message": "Archivo recibido y procesado correctamente",
        "filename": saved_path.name,
        "saved_path": str(saved_path),
        "file_type": file_type,
        "status": "processed",
        "summary": processing["summary"],
    }


@app.post("/generar_csv")
async def generar_csv_endpoint(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre")

    # Accept only .txt
    if not file.filename.lower().endswith(TXT_EXTENSION):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .txt con ISBNs")

    # Save uploaded txt, appending a timestamp if the name already exists.
    original_name = _safe_filename(file.filename or "")
    saved_txt = _ensure_timestamped_path(original_name)

    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    await file.seek(0)
    with saved_txt.open("wb") as output_file:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)

    await file.close()

    # Prepare output directory and filename
    arch_output_dir = ROOT_DIR / "arch_output"
    arch_output_dir.mkdir(parents=True, exist_ok=True)

    out_name = f"{saved_txt.stem}.csv"
    out_path = arch_output_dir / out_name

    # If output exists, append timestamp to avoid overwrite
    if out_path.exists():
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = arch_output_dir / f"{saved_txt.stem}_{ts}.csv"

    # Run generator in thread and capture output
    gen_result = await asyncio.to_thread(_run_generate_csv_with_capture, saved_txt, out_path)
    result_code = int(gen_result.get("result", 1))
    if result_code != 0:
        raise HTTPException(status_code=500, detail=f"Error generando CSV: {gen_result.get('output','')}")

    output_text = gen_result.get("output", "")
    return {
        "message": "CSV generado correctamente",
        "input_txt": saved_txt.name,
        "output_csv": str(out_path),
        "output_lines": output_text.splitlines(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
