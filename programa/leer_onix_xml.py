#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from connect_postgres import open_connection


TAG_ALIASES = {
    "b244": ("idvalue",),  # ISBN
    "b221": ("productidtype",),  # Tipo de id de producto (ISBN, etc.)
    "b012": ("productform",),  # Tipo_Tapa
    "b030": ("titleprefix",),  # Prefijo del título
    "x409": ("titleelementlevel",),  # Tipo_Titulo
    "b031": ("titlewithoutprefix",),  # Título sin prefijo
    "b029": ("subtitle",),  # Subtítulo
    "b203": ("titletext",),  # Título completo
    "b036": ("contributorname", "personname"),  # Autor principal
    "b252": ("languagecode",),  # Lenguaje del texto
    "b204": ("audiencecodetype", "audiencecode",),  # Audiencia
    "x426": ("texttype",), #Tipo de texto de la descripción (para filtrar solo Texto largo)
    "d104": ("text",),  # Descripción HTML
    "x435": ("resourcelink",),  # URL de la imagen de tapa
    "x300": ("addresseename",),  # Proveedor
    "b081": ("publishername",),  # Editorial
    "b067": ("subjectschemeidentifier",),  # Tipo de código BISAC
    "b069": ("subjectcode",),  # Código BISAC
    "b070": ("subjectheadingtext",),  # Categoría BISAC
}


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _is_tag(element: ET.Element, tag_name: str) -> bool:
    """Return True if element's local name matches tag_name or any of its aliases."""
    candidate_names = [tag_name, *TAG_ALIASES.get(tag_name.lower(), ())]
    candidate_names = {candidate.lower() for candidate in candidate_names if candidate}
    return _local_name(element.tag).lower() in candidate_names


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _iter_product_elements(root: ET.Element) -> Iterable[ET.Element]:
    if _is_tag(root, "product"):
        yield root
        return

    for element in root.iter():
        if _is_tag(element, "product"):
            yield element


def _first_text(element: ET.Element, tag_name: str) -> str:
    candidate_names = [tag_name, *TAG_ALIASES.get(tag_name.lower(), ())]
    candidate_names = {candidate.lower() for candidate in candidate_names if candidate}

    for child in element.iter():
        if _local_name(child.tag).lower() in candidate_names:
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
        if not _is_tag(subject, "subject"):
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
        if _is_tag(element, "onixmessage"):
            release = element.get("release", "").strip()
            if release:
                return release
    return ""


def _extract_proveedor(root: ET.Element) -> str:
    """Extract proveedor from x300 (AddresseeName) tag."""
    # Prefer direct element match (accepting aliases), fallback to _first_text
    for elem in root.iter():
        if _is_tag(elem, "x300"):
            return _clean_text(elem.text)
    return _first_text(root, "x300")


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
                    WITH inserted AS (
                        INSERT INTO archivo (nombre, proveedor, onix_version)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (nombre) DO NOTHING
                        RETURNING id_archivo
                    )
                    SELECT id_archivo
                    FROM inserted
                    UNION ALL
                    SELECT id_archivo
                    FROM archivo
                    WHERE nombre = %s
                    LIMIT 1
                    """,
                    (nombre, proveedor, onix_version, nombre),
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


def _build_titulo(product: ET.Element) -> str:
    """
    Build title according to rules:
    - Only consider titleelement with x409 = "01"
    - If b203 exists: use b203 + b029
    - If b203 doesn't exist: use b030 + b031 (+ b029 after b031)
    - If x409 = "02" exists, concatenate it to the title
    """
    titulo_parts = []
    titulo_02 = ""

    # Find all titleelement elements
    for title_element in product.iter():
        if not _is_tag(title_element, "titleelement"):
            continue

        x409 = _first_text(title_element, "x409")

        if x409 == "01":
            b203 = _first_text(title_element, "b203")
            b030 = _first_text(title_element, "b030")
            b031 = _first_text(title_element, "b031")
            b029 = _first_text(title_element, "b029")

            if b203:
                titulo_parts.append(b203)
                if b029:
                    titulo_parts.append(b029)
            else:
                if b030:
                    titulo_parts.append(b030)
                if b031:
                    titulo_parts.append(b031)
                if b029:
                    titulo_parts.append(b029)

        elif x409 == "02":
            b203 = _first_text(title_element, "b203")
            b030 = _first_text(title_element, "b030")
            b031 = _first_text(title_element, "b031")
            b029 = _first_text(title_element, "b029")

            if b203:
                titulo_02 = " ".join(part for part in (b203, b029) if part).strip()
            else:
                parts = []
                if b030:
                    parts.append(b030)
                if b031:
                    parts.append(b031)
                if b029:
                    parts.append(b029)
                titulo_02 = " ".join(parts).strip()

    # Concatenate x409=02 if exists
    if titulo_02:
        titulo_parts.append(titulo_02)

    return " ".join(titulo_parts).strip()


def _find_isbn_for_product(product: ET.Element, target_type: str = "15") -> str:
    """
    Find the IDValue (b244) that belongs to a ProductIdentifier whose
    ProductIDType (b221) equals `target_type`. Returns empty string if
    no matching ProductIdentifier is found.
    """
    for elem in product.iter():
        if not _is_tag(elem, "productidentifier"):
            continue

        pid_type = _first_text(elem, "b221")
        if str(pid_type).strip() == str(target_type):
            return _clean_text(_first_text(elem, "b244"))

    return ""


def _extract_descripcion_html(product: ET.Element) -> str:
    """
    Extract the d104 text that follows x426=03.
    If x426=03 does not exist, fall back to the d104 that follows x426=01.
    If neither exists, return the first d104 found.
    """
    first_d104 = ""
    descripcion_01 = ""
    pending_texttype = ""

    # Prepare candidate name sets including aliases (long tags)
    x426_names = {n.lower() for n in ("x426", *TAG_ALIASES.get("x426", ())) if n}
    d104_names = {n.lower() for n in ("d104", *TAG_ALIASES.get("d104", ())) if n}

    for elem in product.iter():
        tag_local = _local_name(elem.tag).lower()

        if tag_local in x426_names:
            pending_texttype = _clean_text(elem.text)
            continue

        if tag_local not in d104_names:
            continue

        descripcion = _clean_text(elem.text)
        if not descripcion:
            pending_texttype = ""
            continue

        if not first_d104:
            first_d104 = descripcion

        if pending_texttype == "03":
            return descripcion

        if pending_texttype == "01" and not descripcion_01:
            descripcion_01 = descripcion

        pending_texttype = ""

    return descripcion_01 or first_d104


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
        # Use the ISBN only when it's the IDValue for a ProductIdentifier
        # whose ProductIDType (b221) == 15 (per user requirement).
        "isbn": _find_isbn_for_product(product, "15"),
        "tipo_tapa": _first_text(product, "b012"),
        "titulo": _build_titulo(product),
        "autor": _first_text(product, "b036"),
        "lenguaje": lenguaje,
        "audiencia": _first_text(product, "b204"),
        "descripcion_html": _extract_descripcion_html(product),
        "url_tapa": _first_text(product, "x435"),
        "editorial": _first_text(product, "b081"),
        "bisac": bisac_entries,
        "tag": _compose_final_tags(base_tags),
    }
    return record


def parse_onix_file(xml_path: str | Path) -> list[dict[str, object]]:
    path = Path(xml_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo ONIX: {path}")

    bisac_map = _load_bisac_tag_map()
    products: list[dict[str, object]] = []
    for _, element in ET.iterparse(path, events=("end",)):
        if _is_tag(element, "product"):
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


def _insert_products_to_db(
    products: list[dict[str, object]],
    id_archivo: int | None = None,
) -> tuple[int, int, int, int]:
    """
    Insert products into the onix table using UPSERT and detailed counters.
    Args:
        products: List of product dictionaries to insert
        id_archivo: Optional foreign key to archivo table
    Returns: (inserted_count, updated_count, skipped_count, unchanged_count)
    """
    rows_to_upsert: list[tuple[str, str, str, str, str, str, str, str, str, str, int | None]] = []
    skipped = 0
    inserted = 0
    updated = 0
    unchanged = 0

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

        rows_to_upsert.append(
            (isbn, tipo_tapa, titulo, autor, lenguaje, audiencia, 
             descripcion, url_tapa, editorial, tag, id_archivo)
        )

    if not rows_to_upsert:
        return 0, 0, skipped, 0

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                for row in rows_to_upsert:
                    cur.execute(
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
                    WHERE (
                        onix.tipo_tapa,
                        onix.titulo,
                        onix.autor,
                        onix.lenguaje,
                        onix.audiencia,
                        onix.descripcion,
                        onix.url_tapa,
                        onix.editorial,
                        onix.tag,
                        onix.id_archivo
                    ) IS DISTINCT FROM (
                        EXCLUDED.tipo_tapa,
                        EXCLUDED.titulo,
                        EXCLUDED.autor,
                        EXCLUDED.lenguaje,
                        EXCLUDED.audiencia,
                        EXCLUDED.descripcion,
                        EXCLUDED.url_tapa,
                        EXCLUDED.editorial,
                        EXCLUDED.tag,
                        EXCLUDED.id_archivo
                    )
                    RETURNING (xmax = 0) AS inserted
                    """,
                    row,
                    )

                    result = cur.fetchone()
                    if result is None:
                        unchanged += 1
                    elif result[0]:
                        inserted += 1
                    else:
                        updated += 1
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error durante inserción en base de datos: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()

    return inserted, updated, skipped, unchanged


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        xml_path = Path(args.xml_path)
        
        # Parse the root to extract archivo information
        root = ET.parse(xml_path).getroot()
        id_archivo = _insert_archivo(xml_path, root)
        
        products = parse_onix_file(xml_path)

        # Insert products into database with archivo reference
        inserted, updated, skipped, unchanged = _insert_products_to_db(products, id_archivo)
        print("Resumen de carga ONIX:")
        print(f"- Total leidos: {len(products)}")
        print(f"- Registros insertados: {inserted}")
        print(f"- Registros modificados: {updated}")
        print(f"- Registros saltados: {skipped}")
        print(f"- Registros sin cambios: {unchanged}")

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