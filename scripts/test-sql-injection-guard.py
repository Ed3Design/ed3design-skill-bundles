#!/usr/bin/env python3
"""Regression test for SQL-injection guard in db-schema-inspector.py.

Runs without external services — only imports the module and exercises
the identifier-validator. Intended for CI smoke-test.
"""

import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "token-savers" / "tools" / "db-schema-inspector.py"
spec = importlib.util.spec_from_file_location("dbsi", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def expect_ok(name: str):
    """Identifier must pass validation untouched."""
    result = mod._validate_identifier("test", name)
    assert result == name, f"expected {name!r} to pass; got {result!r}"


def expect_reject(name):
    """Identifier must raise ValueError."""
    try:
        mod._validate_identifier("test", name)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for {name!r} but passed")


# Accepted: simple identifiers
for ok in ("users", "user_table", "_private", "Tbl1", "a", "_"):
    expect_ok(ok)

# Rejected: classic injection payloads + special chars
for bad in (
    "users; DROP TABLE foo",                     # statement chaining
    "users' OR 1=1 --",                          # boolean injection
    "users\\'; DROP TABLE foo; --",              # escape-quote injection
    "public.users",                              # dotted (qualified) ident
    "\"users\"",                                 # quoted ident
    "users users",                               # space
    "1users",                                    # leading digit
    "",                                          # empty
    " ",                                         # whitespace
    None,                                        # wrong type
    "a" * 64,                                    # over length limit (63 max)
):
    expect_reject(bad)

print("PASS: SQL-injection guard rejects all 11 attack payloads and accepts 6 valid identifiers")
