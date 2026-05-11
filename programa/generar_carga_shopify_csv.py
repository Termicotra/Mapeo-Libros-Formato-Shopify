#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from connect_postgres import open_connection

CSV_COLUMNS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare At Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Variant Barcode",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Gift Card",
    "product.metafields.custom.autor",
    "product.metafields.shopify.language-version",
    "product.metafields.shopify.target-audience",
    "product.metafields.shopify.book-cover-type",
    "product.metafields.shopify.genre",
    "Status",
]


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _exact_lookup_key(value: object) -> str:
    return _normalize_text(value).lower()


def _language_version(language: str) -> str:
    if language == "spa":
        return "spa-spanish"
    if language == "eng":
        return "eng-english"
    return ""


def _load_idioma_map() -> dict[str, str]:
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT idioma, valor_shopify
                    FROM idioma
                    WHERE COALESCE(idioma, '') <> ''
                      AND COALESCE(valor_shopify, '') <> ''
                    ORDER BY id_idioma
                    """
                )
                mapping: dict[str, str] = {}
                for idioma, valor_shopify in cur.fetchall():
                    key = _exact_lookup_key(idioma)
                    if key and key not in mapping:
                        mapping[key] = _normalize_text(valor_shopify)
                return mapping
    finally:
        conn.close()


def _load_tapa_map() -> dict[str, str]:
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tapa, valor_shopify
                    FROM tapa
                    WHERE COALESCE(tapa, '') <> ''
                      AND COALESCE(valor_shopify, '') <> ''
                    ORDER BY id_tapa
                    """
                )
                mapping: dict[str, str] = {}
                for tapa_value, valor_shopify in cur.fetchall():
                    key = _exact_lookup_key(tapa_value)
                    if key and key not in mapping:
                        mapping[key] = _normalize_text(valor_shopify)
                return mapping
    finally:
        conn.close()


def _resolve_with_fallback(source_value: str, mapping: dict[str, str], fallback_func) -> str:
    """Helper to resolve mapped value with fallback to function if no match."""
    source_key = _exact_lookup_key(source_value)
    if source_key:
        for mapped_key, mapped_value in mapping.items():
            if mapped_key and (mapped_key in source_key or source_key in mapped_key):
                return mapped_value
    return fallback_func(source_value)


def _target_audience(tags: str) -> str:
    normalized_tags = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}
    if "infantil" in normalized_tags:
        return "kids"
    if "juvenil" in normalized_tags:
        return "young-adults"
    return "adults"


def _cover_type(tipo_tapa: str) -> str:
    if tipo_tapa == "BB":
        return "tapa-dura"
    if tipo_tapa == "BC":
        return "tapa-blanda"
    return ""


def _fetch_metadato_rows() -> list[dict[str, str]]:
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT isbn, titulo, descripcion, autor, lenguaje, tipo_tapa, tag, url_tapa
                    FROM metadato
                    ORDER BY isbn
                    """
                )
                rows: list[dict[str, str]] = []
                for isbn, titulo, descripcion, autor, lenguaje, tipo_tapa, tag, url_tapa in cur.fetchall():
                    rows.append(
                        {
                            "isbn": _normalize_text(isbn),
                            "titulo": _normalize_text(titulo),
                            "descripcion": _normalize_text(descripcion),
                            "autor": _normalize_text(autor),
                            "lenguaje": _normalize_text(lenguaje),
                            "tipo_tapa": _normalize_text(tipo_tapa),
                            "tag": _normalize_text(tag),
                            "url_tapa": _normalize_text(url_tapa),
                        }
                    )
                return rows
    finally:
        conn.close()


def _build_row(
    record: dict[str, str],
    idioma_map: dict[str, str],
    tapa_map: dict[str, str],
) -> dict[str, str]:
    isbn = record["isbn"]
    titulo = record["titulo"]
    descripcion = record["descripcion"]
    autor = record["autor"]
    lenguaje = record["lenguaje"]
    tipo_tapa = record["tipo_tapa"]
    tag = record["tag"]
    url_tapa = record["url_tapa"]

    return {
        "Handle": isbn,
        "Title": titulo,
        "Body (HTML)": descripcion,
        "Vendor": autor,
        "Product Category": "Libros Impresos",
        "Type": "Libro",
        "Tags": tag,
        "Published": "TRUE",
        "Option1 Name": "",
        "Option1 Value": "",
        "Variant SKU": "",
        "Variant Grams": "0",
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": "0",
        "Variant Inventory Policy": "deny",
        "Variant Fulfillment Service": "manual",
        "Variant Price": "0",
        "Variant Compare At Price": "",
        "Variant Requires Shipping": "TRUE",
        "Variant Taxable": "FALSE",
        "Variant Barcode": isbn,
        "Image Src": url_tapa,
        "Image Position": "",
        "Image Alt Text": "",
        "Gift Card": "False",
        "product.metafields.custom.autor": autor,
        "product.metafields.shopify.language-version": _resolve_with_fallback(
            lenguaje,
            idioma_map,
            _language_version,
        ),
        "product.metafields.shopify.target-audience": _target_audience(tag),
        "product.metafields.shopify.book-cover-type": _resolve_with_fallback(
            tipo_tapa,
            tapa_map,
            _cover_type,
        ),
        "product.metafields.shopify.genre": "",
        "Status": "active",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera un CSV de carga para Shopify desde la tabla metadato.")
    parser.add_argument(
        "--output",
        default="carga_shopify.csv",
        help="Ruta del archivo CSV de salida. Por defecto: carga_shopify.csv",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = Path(args.output)

    try:
        records = _fetch_metadato_rows()
        idioma_map = _load_idioma_map()
        tapa_map = _load_tapa_map()
        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(_build_row(record, idioma_map, tapa_map))

        print(f"CSV generado en: {output_path} ({len(records)} registros)")
        return 0
    except Exception as exc:
        print(f"Error al generar CSV Shopify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
