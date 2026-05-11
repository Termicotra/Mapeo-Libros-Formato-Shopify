#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for file processing."""
    parser = argparse.ArgumentParser(
        description="Procesa archivos XML o CSV: carga en tabla raw y luego en metadato",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "archivo",
        type=str,
        help="Ruta del archivo XML o CSV a procesar",
    )
    return parser


def _detect_file_type(file_path: Path) -> str:
    """Detect if file is XML or CSV based on extension."""
    suffix = file_path.suffix.lower()
    
    if suffix == ".xml":
        return "xml"
    elif suffix == ".csv":
        return "csv"
    else:
        raise ValueError(f"Tipo de archivo no reconocido: {suffix}. Use .xml o .csv")


def _process_xml(file_path: Path) -> int:
    """Process XML file using leer_onix_xml module."""
    try:
        from leer_onix_xml import main as leer_xml_main
    except ImportError as e:
        print(f"Error importando módulo leer_onix_xml: {e}", file=sys.stderr)
        return 1
    
    print(f"Procesando archivo XML: {file_path}")
    print("-" * 60)
    
    result = leer_xml_main([str(file_path)])
    if result != 0:
        print(f"Error al procesar archivo XML", file=sys.stderr)
        return result
    
    return 0


def _process_csv(file_path: Path) -> int:
    """Process CSV file using leer_metadato_csv module."""
    try:
        from leer_metadato_csv import main as leer_csv_main
    except ImportError as e:
        print(f"Error importando módulo leer_metadato_csv: {e}", file=sys.stderr)
        return 1
    
    print(f"Procesando archivo CSV: {file_path}")
    print("-" * 60)
    
    result = leer_csv_main([str(file_path)])
    if result != 0:
        print(f"Error al procesar archivo CSV", file=sys.stderr)
        return result
    
    return 0


def _transform_raw_to_metadato() -> int:
    """Transform records from raw table to metadato table."""
    try:
        from procesar_raw_a_metadato import main as procesar_main
    except ImportError as e:
        print(f"Error importando módulo procesar_raw_a_metadato: {e}", file=sys.stderr)
        return 1
    
    print("\n" + "=" * 60)
    print("Transformando registros de raw a metadato")
    print("=" * 60)
    
    result = procesar_main()
    if result != 0:
        print(f"Error al transformar registros", file=sys.stderr)
        return result
    
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for file processing."""
    args = build_parser().parse_args(argv)
    
    try:
        file_path = Path(args.archivo)
        
        # Validate file exists
        if not file_path.exists():
            print(f"Error: Archivo no encontrado: {file_path}", file=sys.stderr)
            return 1
        
        # Detect file type
        file_type = _detect_file_type(file_path)
        print(f"Tipo de archivo detectado: {file_type.upper()}")
        print()
        
        # Process file based on type
        if file_type == "xml":
            result = _process_xml(file_path)
        else:  # csv
            result = _process_csv(file_path)
        
        if result != 0:
            return result
        
        # Transform raw records to metadato
        result = _transform_raw_to_metadato()
        
        if result == 0:
            print("\n" + "=" * 60)
            print("✓ Procesamiento completado exitosamente")
            print("=" * 60)
        
        return result
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error fatal durante procesamiento: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
