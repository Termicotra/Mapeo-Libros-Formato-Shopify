#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path


REQUIRED_TABLES = ("bisac", "metadato")
SCHEMA_SQL_PATH = Path(__file__).with_name("generar_tablas_postgresql.sql")


def _conn_params() -> dict:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"conninfo": database_url}

    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "admin"),
        "dbname": os.getenv("PGDATABASE", "db_bisac"),
    }


def _load_schema_sql() -> str:
    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"No se encontró el script SQL: {SCHEMA_SQL_PATH}")
    return SCHEMA_SQL_PATH.read_text(encoding="utf-8")


def _missing_tables(cur) -> list[str]:
    missing: list[str] = []
    for table_name in REQUIRED_TABLES:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            );
            """,
            (table_name,),
        )
        exists = cur.fetchone()[0]
        if not exists:
            missing.append(table_name)
    return missing


def _verify_and_initialize_schema(conn) -> None:
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()

            missing = _missing_tables(cur)
            if not missing:
                print("Conexión exitosa. Todas las tablas requeridas ya existen.")
                return

            schema_sql = _load_schema_sql()
            cur.execute(schema_sql)
            print(
                "Se crearon tablas faltantes usando el script SQL: "
                f"{', '.join(missing)}"
            )


def open_connection(ensure_schema: bool = False):
    """Abre una conexion PostgreSQL usando psycopg o psycopg2."""
    params = _conn_params()
    psycopg_error: Exception | None = None

    try:
        import psycopg  # type: ignore

        if "conninfo" in params:
            conn = psycopg.connect(params["conninfo"], connect_timeout=5)
        else:
            conn = psycopg.connect(connect_timeout=5, **params)

        if ensure_schema:
            _verify_and_initialize_schema(conn)

        return conn
    except Exception as e:
        psycopg_error = e

    try:
        import psycopg2  # type: ignore

        if "conninfo" in params:
            conn = psycopg2.connect(params["conninfo"], connect_timeout=5)
        else:
            conn = psycopg2.connect(connect_timeout=5, **params)

        if ensure_schema:
            _verify_and_initialize_schema(conn)

        return conn
    except Exception as e2:
        raise RuntimeError(
            "No se pudo conectar usando psycopg ni psycopg2. "
            f"Error psycopg: {psycopg_error}. Error psycopg2: {e2}"
        ) from e2


def main() -> int:
    try:
        conn = open_connection(ensure_schema=True)
        conn.close()
        return 0

    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
