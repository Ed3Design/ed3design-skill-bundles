#!/usr/bin/env python3
"""db-schema-inspector.py — Erfüllt CLAUDE.md SQL-Maxime „Spalten via Schema verifizieren".

Sprint 2 Item 5b aus token-optimierung-Roadmap (12.06.2026).

Pattern: statt `\\d table` + ad-hoc Output-Parsen ein strukturiertes JSON
mit column_name + data_type + is_nullable + column_default pro Spalte.
Verhindert „Wishful-Column"-Anti-Pattern (08.06.2026 v3-Briefing-Bug).

Default-Connection: swatserver ultimative-platform DB via ssh+docker exec.
Override per `--db-url` oder env `DB_INSPECTOR_URL`.

Usage:
    db-schema-inspector.py v3_signals
    db-schema-inspector.py v3_trades --connection ultimative
    db-schema-inspector.py mieter --connection mfh
    db-schema-inspector.py x --db-url postgresql://user:pass@host/db

Output (JSON):
    {
      "table": "v3_signals",
      "schema": "public",
      "column_count": 23,
      "columns": [
        {"name": "id", "type": "integer", "nullable": false, "default": "nextval(...)"},
        ...
      ]
    }

Token-Cost: ~50-200 Tokens pro Inspect (vs ~500-1500 für `\\d table` Raw-Output).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys

# ──────────────────────────────────────────────────────────────────────────
# Config — Pre-Defined Connections (Wolf-Setup-spezifisch)
# ──────────────────────────────────────────────────────────────────────────

CONNECTIONS = {
    # ultimative-platform Trading-DB (default)
    "ultimative": {
        "ssh_host": "eddie@swatserver",
        "container": "ultimative-db",
        "user": "eddie",
        "db": "trader",
    },
    # Mietverwaltung-DB
    "mfh": {
        "ssh_host": "eddie@swatserver",
        "container": "hausverwaltung-loebejun-hausverwaltung-db-1",
        "user": "eddie",
        "db": "mfh",
    },
    # pvista PV-Monitor-DB
    "pvista": {
        "ssh_host": "eddie@swatserver",
        "container": "pvista-db",
        "user": "pvista",
        "db": "pvista",
    },
}

DEFAULT_CONNECTION = "ultimative"

# ──────────────────────────────────────────────────────────────────────────
# Core SQL
# ──────────────────────────────────────────────────────────────────────────

SCHEMA_QUERY = """
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = '{table}'
  AND table_schema = '{schema}'
ORDER BY ordinal_position;
"""


def build_ssh_command(conn: dict, sql: str) -> list[str]:
    """Build ssh+docker exec command list (argv-style, no shell injection)."""
    psql_cmd = (
        f"docker exec {shlex.quote(conn['container'])} "
        f"psql -U {shlex.quote(conn['user'])} "
        f"-d {shlex.quote(conn['db'])} "
        f"-A -t -F '|' -c {shlex.quote(sql)}"
    )
    return ["ssh", conn["ssh_host"], psql_cmd]


def query_schema(connection_name: str, table: str, schema: str = "public") -> dict:
    """Execute schema-inspect query against pre-defined connection."""
    if connection_name not in CONNECTIONS:
        raise ValueError(
            f"Unknown connection '{connection_name}'. "
            f"Available: {list(CONNECTIONS.keys())}"
        )

    conn = CONNECTIONS[connection_name]
    sql = SCHEMA_QUERY.format(table=table, schema=schema).strip()

    cmd = build_ssh_command(conn, sql)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=15
    )

    if result.returncode != 0:
        return {
            "table": table,
            "schema": schema,
            "error": result.stderr.strip() or f"exit {result.returncode}",
            "columns": [],
        }

    rows = [
        line.strip().split("|")
        for line in result.stdout.strip().split("\n")
        if line.strip()
    ]

    columns = [
        {
            "name": r[0],
            "type": r[1],
            "nullable": r[2] == "YES",
            "default": r[3] if r[3] else None,
        }
        for r in rows
        if len(r) >= 4
    ]

    return {
        "table": table,
        "schema": schema,
        "connection": connection_name,
        "column_count": len(columns),
        "columns": columns,
    }


def query_via_url(db_url: str, table: str, schema: str = "public") -> dict:
    """Override-Pfad: lokales psql via DB-URL statt ssh+docker."""
    sql = SCHEMA_QUERY.format(table=table, schema=schema).strip()
    cmd = ["psql", db_url, "-A", "-t", "-F", "|", "-c", sql]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    if result.returncode != 0:
        return {
            "table": table,
            "schema": schema,
            "error": result.stderr.strip(),
            "columns": [],
        }

    rows = [
        line.strip().split("|")
        for line in result.stdout.strip().split("\n")
        if line.strip()
    ]

    columns = [
        {
            "name": r[0],
            "type": r[1],
            "nullable": r[2] == "YES",
            "default": r[3] if r[3] else None,
        }
        for r in rows
        if len(r) >= 4
    ]

    return {
        "table": table,
        "schema": schema,
        "connection": "url-direct",
        "column_count": len(columns),
        "columns": columns,
    }


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(
        description="Schema-Inspect für Tabellen via information_schema."
    )
    p.add_argument("table", help="Tabellen-Name (z.B. v3_signals)")
    p.add_argument(
        "--connection",
        "-c",
        default=os.environ.get("DB_INSPECTOR_CONN", DEFAULT_CONNECTION),
        help=f"Pre-defined connection ({list(CONNECTIONS.keys())}); default 'ultimative'",
    )
    p.add_argument(
        "--db-url",
        default=os.environ.get("DB_INSPECTOR_URL"),
        help="Override: postgresql://...-URL für lokales psql (skipt ssh+docker)",
    )
    p.add_argument(
        "--schema",
        default="public",
        help="Schema-Name (default: public)",
    )
    p.add_argument(
        "--names-only",
        action="store_true",
        help="Output nur Column-Namen-Array (kompakteste Form, ~10-30 Tokens)",
    )
    args = p.parse_args()

    try:
        if args.db_url:
            result = query_via_url(args.db_url, args.table, args.schema)
        else:
            result = query_schema(args.connection, args.table, args.schema)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2

    if args.names_only:
        # Ultra-compact mode: nur Namen-Liste
        print(
            json.dumps(
                {
                    "table": result["table"],
                    "columns": [c["name"] for c in result.get("columns", [])],
                    "count": result.get("column_count", 0),
                }
            )
        )
    else:
        print(json.dumps(result, indent=2))

    if "error" in result:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
