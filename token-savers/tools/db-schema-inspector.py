#!/usr/bin/env python3
"""db-schema-inspector.py — Schema verification via information_schema.

Pattern: instead of `\\d table` + ad-hoc output parsing, structured JSON with
column_name + data_type + is_nullable + column_default per column. Prevents
"wishful-column" anti-pattern (SELECT on non-existent columns).

Usage:
    db-schema-inspector.py <table>                       # uses default connection
    db-schema-inspector.py <table> --connection <name>   # named connection from config
    db-schema-inspector.py <table> --db-url postgresql://user:pass@host/db
    db-schema-inspector.py --init                        # write example config

Configuration:
    Reads ~/.config/db-schema-inspector/config.json. Example:

    {
      "connections": {
        "myapp": {
          "ssh_host": "user@server",
          "container": "myapp-db",
          "user": "dbuser",
          "db": "myapp"
        },
        "local": {
          "db_url": "postgresql://user:pass@localhost/mydb"
        }
      },
      "default_connection": "myapp"
    }

Output (JSON):
    {
      "table": "<table>",
      "schema": "public",
      "column_count": N,
      "columns": [
        {"name": "id", "type": "integer", "nullable": false, "default": "nextval(...)"},
        ...
      ]
    }

Token cost: ~50-200 tokens per inspect (vs ~500-1500 for `\\d table` raw output).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────
# Config loading
# ──────────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".config" / "db-schema-inspector" / "config.json"

EXAMPLE_CONFIG = {
    "connections": {
        "example-ssh": {
            "ssh_host": "user@server",
            "container": "myapp-db",
            "user": "dbuser",
            "db": "myapp"
        },
        "example-local": {
            "db_url": "postgresql://user:pass@localhost/mydb"
        }
    },
    "default_connection": "example-ssh"
}


def load_config() -> dict:
    """Load config from ~/.config/db-schema-inspector/config.json or return empty."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠ Config-load error: {e}", file=sys.stderr)
        return {}


def init_config() -> int:
    """Write example config to ~/.config/db-schema-inspector/config.json."""
    if CONFIG_PATH.exists():
        print(f"Config already exists: {CONFIG_PATH}", file=sys.stderr)
        return 1
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(EXAMPLE_CONFIG, indent=2))
    print(f"✅ Example config written to {CONFIG_PATH}")
    print("   Edit connections + default_connection for your setup.")
    return 0


CONFIG = load_config()
CONNECTIONS = CONFIG.get("connections", {})
DEFAULT_CONNECTION = CONFIG.get("default_connection")

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
        description="Schema inspect for tables via information_schema."
    )
    p.add_argument("table", nargs="?", help="Table name (e.g. v3_signals)")
    p.add_argument(
        "--init", action="store_true",
        help=f"Write example config to {CONFIG_PATH} and exit",
    )
    p.add_argument(
        "--connection", "-c",
        default=os.environ.get("DB_INSPECTOR_CONN", DEFAULT_CONNECTION),
        help=f"Named connection from config ({list(CONNECTIONS.keys()) or 'none configured'})",
    )
    p.add_argument(
        "--db-url",
        default=os.environ.get("DB_INSPECTOR_URL"),
        help="Override: postgresql://...-URL for direct psql (skips ssh+docker)",
    )
    p.add_argument(
        "--schema", default="public",
        help="Schema name (default: public)",
    )
    p.add_argument(
        "--names-only", action="store_true",
        help="Output only column name array (most compact, ~10-30 tokens)",
    )
    args = p.parse_args()

    if args.init:
        return init_config()

    if not args.table:
        p.error("table is required (or use --init to write example config)")

    if not args.db_url and not args.connection:
        print("ERROR: No connection configured.", file=sys.stderr)
        print(f"  Either: db-schema-inspector.py --init   (write example config)", file=sys.stderr)
        print(f"  Or:     db-schema-inspector.py <table> --db-url postgresql://...", file=sys.stderr)
        return 2

    # Allow connection-as-db_url via config
    if args.connection and args.connection in CONNECTIONS:
        conn_def = CONNECTIONS[args.connection]
        if "db_url" in conn_def and not args.db_url:
            args.db_url = conn_def["db_url"]

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
