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


def _language_version(language: str) -> str:
    if language == "spa":
        return "spa-spanish"
    if language == "eng":
        return "eng-english"
    return ""


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


def _build_row(record: dict[str, str]) -> dict[str, str]:
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
        "product.metafields.shopify.language-version": _language_version(lenguaje),
        "product.metafields.shopify.target-audience": _target_audience(tag),
        "product.metafields.shopify.book-cover-type": _cover_type(tipo_tapa),
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
        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(_build_row(record))

        print(f"CSV generado en: {output_path} ({len(records)} registros)")
        return 0
    except Exception as exc:
        print(f"Error al generar CSV Shopify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
