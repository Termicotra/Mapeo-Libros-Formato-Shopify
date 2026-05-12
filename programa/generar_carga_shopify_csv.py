#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
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


def _target_audience(tags: str) -> str:
    normalized_text = _normalize_text(tags).lower()
    normalized_tags = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}

    if (
        "infantil" in normalized_tags
        or "books in english for kids" in normalized_text
        or "books in english for kids" in normalized_tags
    ):
        return "kids"
    if (
        "juvenil" in normalized_tags
        or "books in english for young adults" in normalized_text
        or "books in english for young adults" in normalized_tags
    ):
        return "young-adults"
    return "adults"


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
        # Use values directly from `metadato` (already normalized)
        "product.metafields.shopify.language-version": lenguaje,
        "product.metafields.shopify.target-audience": _target_audience(tag),
        "product.metafields.shopify.book-cover-type": tipo_tapa,
        "product.metafields.shopify.genre": "",
        "Status": "active",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un CSV de carga para Shopify desde la tabla metadato para una lista de ISBNs."
    )
    parser.add_argument(
        "isbns_txt",
        help="Ruta al archivo .txt con los ISBNs (uno por línea).",
    )
    parser.add_argument(
        "--output",
        default="carga_shopify.csv",
        help="Ruta del archivo CSV de salida. Por defecto: carga_shopify.csv",
    )
    return parser


def _read_isbns_from_txt(path: Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de ISBNs: {path}")
    isbns: list[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            v = line.strip()
            if v:
                isbns.append(v)
    return isbns


def _fetch_metadato_rows_for_isbns(isbns: list[str]) -> list[dict[str, str]]:
    if not isbns:
        return []
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(isbns))
                query = f"""
                    SELECT isbn, titulo, descripcion, autor, lenguaje, tipo_tapa, tag, url_tapa
                    FROM metadato
                    WHERE isbn IN ({placeholders})
                    ORDER BY isbn
                    """
                cur.execute(query, tuple(isbns))
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = Path(args.output)

    try:
        isbns = _read_isbns_from_txt(Path(args.isbns_txt))
        if not isbns:
            print("No se encontraron ISBNs en el archivo de entrada.")
            return 1

        records = _fetch_metadato_rows_for_isbns(isbns)
        found_isbns = {record["isbn"] for record in records if record.get("isbn")}
        missing_isbns = [isbn for isbn in isbns if isbn not in found_isbns]

        with output_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(_build_row(record))

        print(f"CSV generado en: {output_path} ({len(records)} registros)")
        if missing_isbns:
            print(f"ISBNs no encontrados en metadato: {len(missing_isbns)}")
            for isbn in missing_isbns:
                print(f"- {isbn}")
        return 0
    except Exception as exc:
        print(f"Error al generar CSV Shopify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
