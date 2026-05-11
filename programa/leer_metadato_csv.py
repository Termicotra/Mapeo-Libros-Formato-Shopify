#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv

import sys
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from connect_postgres import open_connection
from provider_config import detect_provider_by_delimiter, ProviderConfig


# Carga el mapa BISAC -> tags de Shopify de la tabla bisac.
def _load_bisac_tag_map() -> list[str]:
    """
    Load Shopify tags from the database and return them as a flat list.
    Each `tag_shopify` row may contain multiple comma-separated tags, so we
    split them here and keep only the individual tags.
    """
    tags: list[str] = []
    seen: set[str] = set()

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT codigo, tag_shopify
                    FROM bisac
                    WHERE COALESCE(codigo, '') <> '' AND COALESCE(tag_shopify, '') <> ''
                    """
                )

                for _, tag_shopify in cur.fetchall():
                    if not tag_shopify:
                        continue

                    for raw_tag in tag_shopify.split(","):
                        clean_tag = raw_tag.strip().lower()
                        if clean_tag and clean_tag not in seen:
                            seen.add(clean_tag)
                            tags.append(clean_tag)
    finally:
        conn.close()

    return tags


def _load_default_shopify_tag() -> str:
    """Load the Shopify tag configured for the BISAC `default` category."""
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tag_shopify
                    FROM bisac
                    WHERE COALESCE(categoria, '') = 'default'
                      AND COALESCE(tag_shopify, '') <> ''
                    ORDER BY codigo NULLS LAST
                    LIMIT 1
                    """
                )
                result = cur.fetchone()
                return str(result[0]).strip().lower() if result and result[0] else ""
    finally:
        conn.close()


# Normaliza texto para que comparar sea más estable.
def _normalize_for_match(value: str) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


# Deja autores sin caracteres especiales y usa guion como separador.
def _normalize_authors(value: str) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = normalized.replace("|", "-")
    normalized = normalized.replace(";", "-")
    normalized = normalized.replace("/", "-")
    normalized = normalized.replace("&", "-")
    normalized = re.sub(r"[^A-Za-z0-9\- ]+", "", normalized)
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" -")


# Busca coincidencias entre palabras del campo IBIC y los tags de bisac.
def _match_ibic_words_to_tags(csv_value: str, bisac_tags: list[str]) -> list[str]:
    """
    Compare the CSV text against each individual Shopify tag.
    We only keep tags that appear as whole words/phrases in the CSV text,
    which avoids pulling unrelated tags from broad substring matches.
    """
    if not csv_value or not bisac_tags:
        return []

    normalized_csv = _normalize_for_match(csv_value)
    if not normalized_csv:
        return []

    matched_tags: list[str] = []
    seen: set[str] = set()

    for tag_shopify in bisac_tags:
        normalized_tag = _normalize_for_match(tag_shopify)
        if not normalized_tag:
            continue

        pattern = rf"\b{re.escape(normalized_tag)}\b"
        if re.search(pattern, normalized_csv) and tag_shopify not in seen:
            seen.add(tag_shopify)
            matched_tags.append(tag_shopify)

    return matched_tags


# Inserta (o recupera) el archivo CSV en DB y devuelve su id_archivo.
def _insert_archivo_csv(csv_path: Path, provider_name: str = "") -> int:
    """
    Inserta un registro en la tabla `archivo` usando el nombre del archivo CSV.
    Devuelve `id_archivo` existente o recién creado.
    """
    path = Path(csv_path)
    nombre = path.name

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH inserted AS (
                        INSERT INTO archivo (nombre, proveedor, onix_version)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (nombre) DO NOTHING
                        RETURNING id_archivo
                    )
                    SELECT id_archivo FROM inserted
                    UNION ALL
                    SELECT id_archivo FROM archivo WHERE nombre = %s
                    LIMIT 1
                    """,
                    (nombre, provider_name or '', '' , nombre),
                )
                result = cur.fetchone()
                id_archivo = result[0] if result else None
                conn.commit()
                return id_archivo
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# This script reads a CSV (Planeta format) and maps common columns to the
# fields used by the `metadato` table / the existing importer.
# It can output JSON or call the existing DB inserter.


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _map_row_to_record(row: dict[str, str], provider: ProviderConfig) -> dict[str, object]:
    """Map a CSV row to the product record shape using provider configuration.

    Args:
        row: CSV row as dictionary with original column names
        provider: Provider configuration with field mappings

    Returns:
        Normalized product record dictionary
    """
    # Normalize keys: lower, strip for flexible matching
    norm = {k.strip().lower(): v for k, v in row.items()}

    def pick(field_name: str) -> str:
        """Pick a field value from normalized row using provider mapping."""
        csv_column = provider.field_mapping.get(field_name)
        if not csv_column:
            return ""
        
        # Try exact match (case-insensitive)
        v = norm.get(csv_column.lower())
        if v is not None and str(v).strip():
            return _normalize_text(v)
        return ""

    # Map fields using provider configuration
    isbn = pick("isbn")
    tipo_tapa = pick("tipo_tapa")
    titulo = pick("titulo")
    autor = pick("autor")
    lenguaje = pick("lenguaje")
    audiencia = pick("audiencia")
    descripcion = pick("descripcion")
    url_tapa = pick("url_tapa")
    editorial = pick("editorial")
    tag_value = pick("tag")
    
    autor = _normalize_authors(autor)
    
    record: dict[str, object] = {
        "isbn": isbn,
        "tipo_tapa": tipo_tapa,
        "titulo": titulo,
        "autor": autor,
        "lenguaje": lenguaje,
        "audiencia": audiencia or "",
        "descripcion": descripcion,
        "url_tapa": url_tapa,
        "editorial": editorial,
        "tag": tag_value,
    }
    
    return record


# Deja un solo registro por ISBN y conserva el primero que aparezca.
def _dedupe_records_by_isbn(records: list[dict[str, object]]) -> list[dict[str, object]]:
    unique_records: list[dict[str, object]] = []
    seen_isbns: set[str] = set()

    for record in records:
        isbn = str(record.get("isbn", "")).strip()
        if not isbn or isbn in seen_isbns:
            continue

        seen_isbns.add(isbn)
        unique_records.append(record)

    return unique_records


def read_csv(path: Path) -> tuple[list[dict[str, object]], ProviderConfig]:
    """Read and parse CSV file, auto-detecting provider.
    
    Args:
        path: Path to CSV file
    
    Returns:
        Tuple of (records list, detected provider config)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If provider cannot be detected
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo CSV: {path}")

    records: list[dict[str, object]] = []
    provider: ProviderConfig | None = None
    
    # Detect delimiter and provider by reading first line
    with path.open(newline="", encoding="latin-1") as fh:
        first_line = fh.readline()
        provider = detect_provider_by_delimiter(first_line)
        
        if not provider:
            raise ValueError(
                f"No se pudo detectar el proveedor del archivo CSV: {path}\n"
                f"Encabezado: {first_line[:100]}"
            )
        
        print(f"✓ Proveedor detectado: {provider.name}")
        
        fh.seek(0)
        reader = csv.DictReader(fh, delimiter=provider.delimiter)
        for row in reader:
            records.append(_map_row_to_record(row, provider))
    
    return _dedupe_records_by_isbn(records), provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lee un CSV y carga datos en la tabla raw.")
    parser.add_argument("csv_path", help="Ruta al archivo CSV de entrada")
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Si se pasa, inserta/actualiza registros en la tabla metadato usando el inserter existente.",
    )

    return parser




def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        csv_path = Path(args.csv_path)

        records, provider = read_csv(csv_path)
        print(f"✓ CSV cargado: {len(records)} registros únicos por ISBN")
        print(f"  Campos mapeados: {', '.join(k for k, v in provider.field_mapping.items() if v)}")

        # Defer to the existing raw inserter in leer_onix_xml to avoid duplication.
        try:
            from leer_onix_xml import _insert_products_to_raw
        except Exception as e:
            print(f"No se pudo importar el inserter: {e}", file=sys.stderr)
            return 1

        # Insert an `archivo` record for this CSV and pass its id to the inserter.
        try:
            id_archivo = _insert_archivo_csv(csv_path, provider.name)
        except Exception as e:
            print(f"No se pudo insertar registro en tabla archivo: {e}", file=sys.stderr)
            return 1

        inserted, updated, unchanged, skipped, error = _insert_products_to_raw(records, id_archivo)
        print("Resumen de carga en tabla raw:")
        print(f"- Total leidos: {len(records)}")
        print(f"- Registros insertados en raw: {inserted}")
        print(f"- Registros actualizados en raw: {updated}")
        print(f"- Registros sin cambios: {unchanged}")
        print(f"- Registros saltados (sin ISBN): {skipped}")
        print(f"- Errores de inserción/actualización: {error}")

        return 0
    except Exception as exc:
        print(f"Error al procesar CSV: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
