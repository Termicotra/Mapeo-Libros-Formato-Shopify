#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from connect_postgres import open_connection


KNOWN_TAG_FIELDS = {
    "b244": "isbn",
    "b012": "tipo_tapa",
    "b030": "prefijo",
    "x409": "tipo_titulo",  
    "b031": "titulo",
    "b203": "titulo_completo",
    "b036": "autor",
    "b252": "lenguaje",
    "b204": "audiencia",
    "d104": "descripcion_html",
    "x435": "url_tapa",
    "x300": "proveedor_onix",
    "b081": "editorial",
    "b069": "bisac_codigo",
    "b070": "bisac_categoria",
}


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _iter_product_elements(root: ET.Element) -> Iterable[ET.Element]:
    if _local_name(root.tag) == "product":
        yield root
        return

    for element in root.iter():
        if _local_name(element.tag) == "product":
            yield element


def _first_text(element: ET.Element, tag_name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == tag_name:
            return _clean_text(child.text)
    return ""


def _load_bisac_tag_map() -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT codigo, tag_shopify
                    FROM bisac
                    WHERE COALESCE(codigo, '') <> ''
                      AND COALESCE(tag_shopify, '') <> ''
                    ORDER BY length(codigo), codigo
                    """
                )

                for codigo, tag_shopify in cur.fetchall():
                    clean_codigo = (codigo or "").strip()
                    clean_tag = (tag_shopify or "").strip()
                    if clean_codigo and clean_tag:
                        mappings.append(
                            {"codigo": clean_codigo, "tag_shopify": clean_tag}
                        )
    finally:
        conn.close()

    return mappings


def _split_shopify_tags(tag_value: str) -> list[str]:
    return [tag.strip() for tag in tag_value.split(",") if tag.strip()]


def _bisac_match_keys(bisac_code: str) -> list[str]:
    cleaned_code = bisac_code.strip().upper()
    if not cleaned_code:
        return []

    keys: list[str] = []

    def _add_key(value: str) -> None:
        if value and value not in keys:
            keys.append(value)

    _add_key(cleaned_code)

    prefix_letters = "".join(character for character in cleaned_code if character.isalpha())[:3]
    prefix_digits = "".join(character for character in cleaned_code if character.isdigit())[:3]

    if prefix_letters:
        if prefix_digits:
            _add_key(f"{prefix_letters}{prefix_digits}")
        _add_key(prefix_letters)

    return keys


def _collect_shopify_tags(bisac_entries: list[dict[str, str]], bisac_map: list[dict[str, str]]) -> str:
    collected: list[str] = []
    seen: set[str] = set()

    for entry in bisac_entries:
        bisac_code = entry.get("codigo", "")
        if not bisac_code:
            continue

        match_keys = _bisac_match_keys(bisac_code)

        for mapping in bisac_map:
            mapping_code = mapping["codigo"].strip().upper()
            if not any(match_key.startswith(mapping_code) for match_key in match_keys):
                continue

            for tag in _split_shopify_tags(mapping["tag_shopify"]):
                if tag not in seen:
                    seen.add(tag)
                    collected.append(tag)

    return ", ".join(collected)


def _compose_final_tags(base_tags: list[str]) -> str:
    final_tags: list[str] = []
    seen: set[str] = set()

    for tag in base_tags:
        clean_tag = tag.strip()
        if clean_tag and clean_tag not in seen:
            seen.add(clean_tag)
            final_tags.append(clean_tag)

    return ", ".join(final_tags)


def _bisac_entries(product: ET.Element, limit: int = 5) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    for subject in product.iter():
        if _local_name(subject.tag) != "subject":
            continue

        scheme_code = _first_text(subject, "b067")
        bisac_code = _first_text(subject, "b069")
        bisac_category = _first_text(subject, "b070")

        if scheme_code != "10" and not bisac_code and not bisac_category:
            continue

        if not bisac_code and not bisac_category:
            continue

        entries.append(
            {
                "scheme_code": scheme_code,
                "codigo": bisac_code,
                "categoria": bisac_category,
            }
        )

        if len(entries) >= limit:
            break

    return entries


def _extract_onix_version(root: ET.Element) -> str:
    """Extract ONIX version from release attribute in ONIXMessage element."""
    for element in root.iter():
        # Case-insensitive tag name comparison
        if _local_name(element.tag).lower() == "onixmessage":
            release = element.get("release", "").strip()
            if release:
                return release
    return ""


def _extract_proveedor(root: ET.Element) -> str:
    """Extract proveedor from x300 (AddresseeName) tag."""
    for element in root.iter():
        if _local_name(element.tag) == "x300":
            proveedor = _clean_text(element.text)
            if proveedor:
                return proveedor
    return ""


def _insert_archivo(
    xml_path: str | Path, root: ET.Element
) -> int:
    """
    Insert archivo record into database and return the id_archivo.
    Extracts:
    - nombre: filename from xml_path
    - proveedor: from x300 tag (AddresseeName)
    - onix_version: from ONIXMessage release attribute
    """
    path = Path(xml_path)
    nombre = path.name
    proveedor = _extract_proveedor(root)
    onix_version = _extract_onix_version(root)

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO archivo (nombre, proveedor, onix_version)
                    VALUES (%s, %s, %s)
                    RETURNING id_archivo
                    """,
                    (nombre, proveedor, onix_version),
                )
                result = cur.fetchone()
                id_archivo = result[0] if result else None
                conn.commit()
                return id_archivo
    finally:
        conn.close()


def _build_titulo(product: ET.Element) -> str:
    """
    Build title according to rules:
    - Only consider titleelement with x409 = "01"
    - If b203 exists: use b203
    - If b203 doesn't exist: use b030 + b031
    - If x409 = "02" exists, concatenate it to the title
    """
    titulo_parts = []
    titulo_02 = ""

    # Find all titleelement elements
    for title_element in product.iter():
        if _local_name(title_element.tag) != "titleelement":
            continue

        x409 = _first_text(title_element, "x409")

        if x409 == "01":
            b203 = _first_text(title_element, "b203")
            b030 = _first_text(title_element, "b030")
            b031 = _first_text(title_element, "b031")

            if b203:
                titulo_parts.append(b203)
            else:
                if b030:
                    titulo_parts.append(b030)
                if b031:
                    titulo_parts.append(b031)

        elif x409 == "02":
            b203 = _first_text(title_element, "b203")
            b030 = _first_text(title_element, "b030")
            b031 = _first_text(title_element, "b031")

            if b203:
                titulo_02 = b203
            else:
                parts = []
                if b030:
                    parts.append(b030)
                if b031:
                    parts.append(b031)
                titulo_02 = " ".join(parts).strip()

    # Concatenate x409=02 if exists
    if titulo_02:
        titulo_parts.append(titulo_02)

    return " ".join(titulo_parts).strip()


def parse_product(
    product: ET.Element,
    bisac_map: list[dict[str, str]],
) -> dict[str, object]:
    bisac_entries = _bisac_entries(product)
    shopify_tags = _collect_shopify_tags(bisac_entries, bisac_map)
    lenguaje = _first_text(product, "b252")

    base_tags = ["todos los libros"]
    if shopify_tags:
        base_tags.extend(_split_shopify_tags(shopify_tags))
    if lenguaje == "eng":
        base_tags.append("books in english")

    record: dict[str, object] = {
        "isbn": _first_text(product, "b244"),
        "tipo_tapa": _first_text(product, "b012"),
        "titulo": _build_titulo(product),
        "autor": _first_text(product, "b036"),
        "lenguaje": lenguaje,
        "audiencia": _first_text(product, "b204"),
        "descripcion_html": "",
        "url_tapa": _first_text(product, "x435"),
        "editorial": _first_text(product, "b081"),
        "bisac": bisac_entries,
        "tag": _compose_final_tags(base_tags),
    }

    for child in product.iter():
        tag_name = _local_name(child.tag)
        if tag_name not in KNOWN_TAG_FIELDS:
            continue

        field_name = KNOWN_TAG_FIELDS[tag_name]
        if field_name == "descripcion_html":
            html_value = child.text or ""
            record["descripcion_html"] = html_value.strip()
    return record


def parse_onix_file(xml_path: str | Path) -> list[dict[str, object]]:
    path = Path(xml_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo ONIX: {path}")

    bisac_map = _load_bisac_tag_map()
    products: list[dict[str, object]] = []
    for _, element in ET.iterparse(path, events=("end",)):
        if _local_name(element.tag) == "product":
            products.append(parse_product(element, bisac_map))
            element.clear()

    if not products:
        root = ET.parse(path).getroot()
        products.extend(
            parse_product(element, bisac_map) for element in _iter_product_elements(root)
        )

    return products


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lee un archivo ONIX XML y extrae los campos principales por producto."
    )
    parser.add_argument("xml_path", help="Ruta al archivo ONIX XML a procesar")
    parser.add_argument(
        "--output",
        help="Ruta del archivo JSON de salida. Por defecto usa el mismo directorio que el XML de entrada.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Imprime el resultado con sangría legible.",
    )
    return parser


def _default_output_path(xml_path: Path) -> Path:
    return xml_path.with_suffix(".json")


def _insert_products_to_db(products: list[dict[str, object]], id_archivo: int | None = None) -> tuple[int, int]:
    """
    Insert products into the onix table using batch processing.
    Uses executemany() for efficiency and ON CONFLICT for safety.
    Args:
        products: List of product dictionaries to insert
        id_archivo: Optional foreign key to archivo table
    Returns: (inserted_count, skipped_count)
    """
    rows_to_insert = []
    skipped = 0

    # Prepare rows, filter out those without ISBN
    for product in products:
        isbn = str(product.get("isbn", "")).strip()
        if not isbn:
            skipped += 1
            continue

        tipo_tapa = str(product.get("tipo_tapa", "")).strip()
        titulo = str(product.get("titulo", "")).strip()
        autor = str(product.get("autor", "")).strip()
        lenguaje = str(product.get("lenguaje", "")).strip()
        audiencia = str(product.get("audiencia", "")).strip()
        descripcion = str(product.get("descripcion_html", "")).strip()
        url_tapa = str(product.get("url_tapa", "")).strip()
        editorial = str(product.get("editorial", "")).strip()
        tag = str(product.get("tag", "")).strip()

        rows_to_insert.append(
            (isbn, tipo_tapa, titulo, autor, lenguaje, audiencia, 
             descripcion, url_tapa, editorial, tag, id_archivo)
        )

    if not rows_to_insert:
        return 0, skipped

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                # Use executemany for batch insert (more efficient than loop)
                cur.executemany(
                    """
                    INSERT INTO onix (isbn, tipo_tapa, titulo, autor, lenguaje, 
                                    audiencia, descripcion, url_tapa, editorial, tag, id_archivo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (isbn) DO UPDATE SET
                        tipo_tapa = EXCLUDED.tipo_tapa,
                        titulo = EXCLUDED.titulo,
                        autor = EXCLUDED.autor,
                        lenguaje = EXCLUDED.lenguaje,
                        audiencia = EXCLUDED.audiencia,
                        descripcion = EXCLUDED.descripcion,
                        url_tapa = EXCLUDED.url_tapa,
                        editorial = EXCLUDED.editorial,
                        tag = EXCLUDED.tag,
                        id_archivo = EXCLUDED.id_archivo
                    """,
                    rows_to_insert,
                )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error durante inserción en batch: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()

    return len(rows_to_insert), skipped


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        xml_path = Path(args.xml_path)
        
        # Parse the root to extract archivo information
        root = ET.parse(xml_path).getroot()
        id_archivo = _insert_archivo(xml_path, root)
        
        products = parse_onix_file(xml_path)

        # Insert products into database with archivo reference
        inserted, skipped = _insert_products_to_db(products, id_archivo)
        print(f"Productos insertados: {inserted}, saltados: {skipped}")

        # Generate JSON output
        output_path = Path(args.output) if args.output else _default_output_path(xml_path)
        output_path.write_text(
            json.dumps(
                products,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
            + "\n",
            encoding="utf-8",
        )

        print(f"JSON generado en: {output_path}")
        return 0
    except Exception as exc:
        print(f"Error al leer el archivo ONIX: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())