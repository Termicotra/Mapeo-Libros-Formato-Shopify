#!/usr/bin/env python3

from __future__ import annotations

import sys
import re
import unicodedata
from connect_postgres import open_connection


def _exact_lookup_key(value: str) -> str:
    """Normalize value to lowercase for case-insensitive matching."""
    return str(value).strip().lower() if value else ""


def _load_idioma_map() -> dict[str, str]:
    """Load language mappings from idioma table."""
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
                        mapping[key] = str(valor_shopify).strip()
                return mapping
    finally:
        conn.close()


def _load_tapa_map() -> dict[str, str]:
    """Load cover type mappings from tapa table."""
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
                        mapping[key] = str(valor_shopify).strip()
                return mapping
    finally:
        conn.close()


def _load_audiencia_map() -> dict[str, str]:
    """Load audience mappings from audiencia table."""
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT audiencia, valor_shopify
                    FROM audiencia
                    WHERE COALESCE(audiencia, '') <> ''
                      AND COALESCE(valor_shopify, '') <> ''
                    ORDER BY id_audiencia
                    """
                )
                mapping: dict[str, str] = {}
                for audiencia_value, valor_shopify in cur.fetchall():
                    key = _exact_lookup_key(audiencia_value)
                    if key and key not in mapping:
                        mapping[key] = str(valor_shopify).strip()
                return mapping
    finally:
        conn.close()


def _resolve_contained_mapped_value(source_value: str, mapping: dict[str, str], fallback=None) -> str:
    """
    Find mapped value by contained-word matching (case-insensitive).
    If no match found and fallback function provided, call it with source_value.
    Otherwise return empty string.
    """
    source_key = _exact_lookup_key(source_value)
    if source_key:
        for mapped_key, mapped_value in mapping.items():
            if mapped_key and (mapped_key in source_key or source_key in mapped_key):
                return mapped_value
    return fallback(source_value) if fallback else ""


def _normalize_for_match(value: str) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _singularize_word(word: str) -> str:
    word = word.strip().lower()
    if not word:
        return ""

    if len(word) > 4 and word.endswith("ces"):
        return word[:-3] + "z"
    if len(word) > 3 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _normalize_for_match_singular(value: str) -> str:
    normalized = _normalize_for_match(value)
    if not normalized:
        return ""

    return " ".join(_singularize_word(part) for part in normalized.split())


def _looks_like_bisac_code(value: str) -> bool:
    cleaned = _exact_lookup_key(value).upper()
    return bool(re.fullmatch(r"[A-Z]{3}(?:\d{3})?(?:\d{3})?", cleaned))


def _load_bisac_codigo_map() -> dict[str, list[str]]:
    """Load BISAC code to Shopify tag mapping from bisac table."""
    mapping: dict[str, list[str]] = {}

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
                    ORDER BY codigo
                    """
                )

                for codigo, tag_shopify in cur.fetchall():
                    clean_codigo = (codigo or "").strip().lower()
                    if clean_codigo:
                        tags = mapping.setdefault(clean_codigo, [])
                        for raw_tag in tag_shopify.split(","):
                            clean_tag = raw_tag.strip().lower()
                            if clean_tag and clean_tag not in tags:
                                tags.append(clean_tag)
    finally:
        conn.close()

    return mapping


def _match_tag_words_to_tags(source_value: str, bisac_tags: list[str]) -> list[str]:
    normalized_source = _normalize_for_match_singular(source_value)
    if not normalized_source or not bisac_tags:
        return []

    matched_tags: list[str] = []
    seen: set[str] = set()

    for tag_shopify in bisac_tags:
        normalized_tag = _normalize_for_match_singular(tag_shopify)
        if not normalized_tag:
            continue

        pattern = rf"\b{re.escape(normalized_tag)}\b"
        if re.search(pattern, normalized_source) and tag_shopify not in seen:
            seen.add(tag_shopify)
            matched_tags.append(tag_shopify)

    return matched_tags


def _resolve_tag_value(
    source_tag: str,
    codigo_map: dict[str, list[str]],
    bisac_tags: list[str],
    default_tag: str,
) -> str:
    """
    Resolve Shopify tag from BISAC codes using progressive matching:
    1. First 3 characters (letters): "FIC"
    2. First 6 characters (3 letters + 3 digits): "FIC059"
    3. Full code (9 characters): "FIC059000"
    
    Each matching level adds its tag if found, no duplicates allowed.
    """
    tags: list[str] = []

    if default_tag:
        tags.append(default_tag)

    seen: set[str] = set()
    if default_tag:
        seen.add(default_tag.strip().lower())

    source_values = [segment.strip() for segment in source_tag.split(",") if segment.strip()]
    if not source_values:
        return ", ".join(tags)

    if not any(_looks_like_bisac_code(value) for value in source_values):
        for matched_tag in _match_tag_words_to_tags(source_tag, bisac_tags):
            clean_tag = matched_tag.strip()
            if clean_tag and clean_tag.lower() not in seen:
                seen.add(clean_tag.lower())
                tags.append(clean_tag)
        return ", ".join(tags)

    # Process each BISAC code from source_tag (comma-separated)
    for codigo_raw in source_values:
        codigo_clean = _exact_lookup_key(codigo_raw).upper()

        if not codigo_clean or len(codigo_clean) < 3:
            continue

        # Try progressively longer prefixes: 3, 6, 9 characters
        for prefix_len in [3, 6, 9]:
            prefix = codigo_clean[:prefix_len]
            prefix_key = _exact_lookup_key(prefix)

            if prefix_key in codigo_map:
                for tag_value in codigo_map[prefix_key]:
                    clean_tag = tag_value.strip()

                    if clean_tag and clean_tag.lower() not in seen:
                        seen.add(clean_tag.lower())
                        tags.append(clean_tag)

    return ", ".join(tags)


def _load_bisac_tag_map() -> list[str]:
    """Load all Shopify tags from bisac table."""
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
    """Load the default Shopify tag from bisac default category."""
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


def _fetch_raw_rows() -> list[dict[str, str]]:
    """Fetch all raw records that haven't been processed yet."""
    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT isbn, tipo_tapa, titulo, autor, lenguaje, audiencia,
                           descripcion, url_tapa, editorial, tag, id_archivo
                    FROM raw
                    ORDER BY isbn
                    """
                )
                rows: list[dict[str, str]] = []
                for row in cur.fetchall():
                    rows.append(
                        {
                            "isbn": str(row[0]).strip() if row[0] else "",
                            "tipo_tapa": str(row[1]).strip() if row[1] else "",
                            "titulo": str(row[2]).strip() if row[2] else "",
                            "autor": str(row[3]).strip() if row[3] else "",
                            "lenguaje": str(row[4]).strip() if row[4] else "",
                            "audiencia": str(row[5]).strip() if row[5] else "",
                            "descripcion": str(row[6]).strip() if row[6] else "",
                            "url_tapa": str(row[7]).strip() if row[7] else "",
                            "editorial": str(row[8]).strip() if row[8] else "",
                            "tag": str(row[9]).strip() if row[9] else "",
                            "id_archivo": row[10] if row[10] else None,
                        }
                    )
                return rows
    finally:
        conn.close()


def _transform_and_insert_to_metadato(
    records: list[dict[str, str]],
    idioma_map: dict[str, str],
    tapa_map: dict[str, str],
    audiencia_map: dict[str, str],
    codigo_map: dict[str, list[str]],
    bisac_tags: list[str],
    default_tag: str,
) -> tuple[int, int, int, int]:
    """Transform records and insert into metadato table."""
    inserted = 0
    updated = 0
    unchanged = 0
    skipped = 0

    conn = open_connection(ensure_schema=False)
    try:
        with conn:
            with conn.cursor() as cur:
                for record in records:
                    isbn = record["isbn"]
                    if not isbn:
                        skipped += 1
                        continue

                    try:
                        tipo_tapa = record["tipo_tapa"]
                        lenguaje = record["lenguaje"]
                        audiencia = record["audiencia"]
                        tag = record["tag"]

                        # Before resolving tags, include audiencia raw into tag source if not present.
                        # This must happen before the language-specific tag replacements.
                        combined_tag_source = str(tag).strip()
                        if audiencia:
                            existing_tags = [t.strip().lower() for t in combined_tag_source.split(",") if t.strip()]
                            audiencia_clean = audiencia.strip()
                            if audiencia_clean and audiencia_clean.lower() not in existing_tags:
                                if combined_tag_source:
                                    combined_tag_source = f"{combined_tag_source}, {audiencia_clean}"
                                else:
                                    combined_tag_source = audiencia_clean

                        # Apply transformations
                        transformed_tipo_tapa = _resolve_contained_mapped_value(tipo_tapa, tapa_map)
                        transformed_lenguaje = _resolve_contained_mapped_value(lenguaje, idioma_map)
                        transformed_audiencia = _resolve_contained_mapped_value(audiencia, audiencia_map)
                        transformed_tag = _resolve_tag_value(combined_tag_source, codigo_map, bisac_tags, default_tag)

                        # If language resolved to English marker, include bisac tags
                        # whose categoria contains 'ingles', and replace any existing tags
                        # with their tag_shopify_ingles equivalents.
                        if str(transformed_lenguaje).strip().lower() == "eng-english":
                            try:
                                # Step 1: Add tags from bisac records with categoria containing 'ingles'
                                cur.execute(
                                    """
                                    SELECT tag_shopify
                                    FROM bisac
                                    WHERE COALESCE(categoria, '') <> ''
                                      AND LOWER(categoria) LIKE %s
                                    ORDER BY codigo
                                    """,
                                    ("%ingles%",),
                                )

                                extra_tags: list[str] = []
                                for (tag_shopify,) in cur.fetchall():
                                    if not tag_shopify:
                                        continue
                                    for part in str(tag_shopify).split(","):
                                        p = part.strip()
                                        if p:
                                            extra_tags.append(p)

                                # Step 2: For each current tag, find its tag_shopify_ingles equivalent
                                current_tags = [t.strip() for t in str(transformed_tag).split(",") if t.strip()]
                                replaced_tags: list[str] = []
                                
                                for current_tag in current_tags:
                                    # Search for this tag in bisac (handle comma-separated values in tag_shopify)
                                    # First, try to find an exact match
                                    cur.execute(
                                        """
                                        SELECT tag_shopify, tag_shopify_ingles
                                        FROM bisac
                                        WHERE COALESCE(tag_shopify, '') <> ''
                                          AND COALESCE(tag_shopify_ingles, '') <> ''
                                        ORDER BY codigo
                                        """,
                                    )
                                    
                                    found_english = None
                                    current_tag_lower = current_tag.lower().strip()
                                    
                                    for tag_shopify_val, tag_shopify_ingles_val in cur.fetchall():
                                        # Split the comma-separated tags and check for match
                                        for individual_tag in str(tag_shopify_val).split(","):
                                            if individual_tag.strip().lower() == current_tag_lower:
                                                found_english = str(tag_shopify_ingles_val).strip()
                                                break
                                        if found_english:
                                            break
                                    
                                    if found_english:
                                        # Use the English version
                                        replaced_tags.append(found_english)
                                    else:
                                        # Keep the original tag if no English version found
                                        replaced_tags.append(current_tag)

                                # Step 3: Merge all tags (replaced + extra) without duplicates
                                all_tags = replaced_tags + extra_tags
                                merged: list[str] = []
                                seen: set[str] = set()
                                for t in all_tags:
                                    key = t.strip().lower()
                                    if key and key not in seen:
                                        seen.add(key)
                                        merged.append(t.strip())
                                
                                if merged:
                                    transformed_tag = ", ".join(merged)
                            except Exception:
                                # If anything goes wrong here, don't fail the whole import;
                                # keep the original transformed_tag and continue.
                                pass

                        values = (
                            isbn,
                            transformed_tipo_tapa,
                            record["titulo"],
                            record["autor"],
                            transformed_lenguaje,
                            transformed_audiencia,
                            record["descripcion"],
                            record["url_tapa"],
                            record["editorial"],
                            transformed_tag,
                            record["id_archivo"],
                        )

                        # Try insert first. If the ISBN already exists, fall back to update only when values changed.
                        cur.execute(
                            """
                            INSERT INTO metadato (isbn, tipo_tapa, titulo, autor, lenguaje,
                                            audiencia, descripcion, url_tapa, editorial, tag, id_archivo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (isbn) DO NOTHING
                            RETURNING 1
                            """,
                            values,
                        )

                        result = cur.fetchone()
                        if result is not None:
                            inserted += 1
                        else:
                            # Record already exists, check if update is needed
                            cur.execute(
                                """
                                SELECT tipo_tapa, titulo, autor, lenguaje, audiencia,
                                       descripcion, url_tapa, editorial, tag, id_archivo
                                FROM metadato
                                WHERE isbn = %s
                                """,
                                (isbn,),
                            )
                            current_row = cur.fetchone()

                            # Compare current values with desired values
                            desired_row = (
                                transformed_tipo_tapa,
                                record["titulo"],
                                record["autor"],
                                transformed_lenguaje,
                                transformed_audiencia,
                                record["descripcion"],
                                record["url_tapa"],
                                record["editorial"],
                                transformed_tag,
                                record["id_archivo"],
                            )

                            if current_row == desired_row:
                                unchanged += 1
                            else:
                                # Values have changed, perform update
                                cur.execute(
                                    """
                                    UPDATE metadato
                                    SET tipo_tapa = %s,
                                        titulo = %s,
                                        autor = %s,
                                        lenguaje = %s,
                                        audiencia = %s,
                                        descripcion = %s,
                                        url_tapa = %s,
                                        editorial = %s,
                                        tag = %s,
                                        id_archivo = %s
                                    WHERE isbn = %s
                                    """,
                                    (
                                        transformed_tipo_tapa,
                                        record["titulo"],
                                        record["autor"],
                                        transformed_lenguaje,
                                        transformed_audiencia,
                                        record["descripcion"],
                                        record["url_tapa"],
                                        record["editorial"],
                                        transformed_tag,
                                        record["id_archivo"],
                                        isbn,
                                    ),
                                )
                                updated += 1
                    except Exception as e:
                        print(f"Error procesando ISBN {record.get('isbn', 'UNKNOWN')}: {e}", file=sys.stderr)

            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error durante transformación e inserción: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()

    return inserted, updated, skipped, unchanged


def main() -> int:
    try:
        print("Cargando mapeos de tablas auxiliares...")
        idioma_map = _load_idioma_map()
        tapa_map = _load_tapa_map()
        audiencia_map = _load_audiencia_map()
        codigo_map = _load_bisac_codigo_map()
        bisac_tags = _load_bisac_tag_map()
        default_tag = _load_default_shopify_tag()

        print("Leyendo registros de tabla raw...")
        records = _fetch_raw_rows()

        if not records:
            print("No hay registros en la tabla raw para procesar.")
            return 0

        print(f"Transformando e insertando {len(records)} registros...")
        inserted, updated, skipped, unchanged = _transform_and_insert_to_metadato(
            records, idioma_map, tapa_map, audiencia_map, codigo_map, bisac_tags, default_tag
        )

        print("Procesamiento completado:")
        print(f"- Registros insertados en metadato: {inserted}")
        print(f"- Registros actualizados en metadato: {updated}")
        print(f"- Registros sin cambios: {unchanged}")
        print(f"- Registros saltados (sin ISBN): {skipped}")

        return 0
    except Exception as exc:
        print(f"Error fatal durante procesamiento: {exc}", file=sys.stderr)
        return 1
 
if __name__ == "__main__":
    raise SystemExit(main())
