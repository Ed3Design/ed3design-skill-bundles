---
name: read-only-sql-via-regex-validator
description: Use when exposing a read-only SQL endpoint to a less-trusted caller (Browser via HTTP, MCP-Tool to LLM, internal Dashboard with copy-paste-able query box, future API consumer). The endpoint accepts a SQL string and must reject all mutating statements before executing. Encodes the regex-based denylist+allowlist pattern from 2026-06-11 ultimative-health Phase-G `/health/sql` endpoint: (1) strip SQL comments (`--` and `/* */`) BEFORE matching to prevent comment-smuggle bypass, (2) normalize whitespace + uppercase, (3) denylist regex for INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE/CALL, (4) allowlist regex for SELECT/WITH/EXPLAIN/ANALYZE start-token. Trigger phrases like "read-only SQL endpoint", "SELECT-only API", "SQL escape hatch", "DB-Query als HTTP-Endpoint", "ad-hoc query interface", "MCP-tool exposes raw SQL", "Postgres read API". Do NOT load if you have a real SQL parser available (e.g. sqlparse, pglast) — use that for production-grade enforcement; this skill is the naive-but-fast-enough pattern for low-stakes internal tools. Do NOT use for write-allowed endpoints (parameterize the writes, don't expose raw SQL), for stored-procedure invocation (regex doesn't reason about side-effects of CALL), or for databases where SELECT itself has side-effects (e.g. SELECT pg_terminate_backend(...) — see Anti-patterns below).
---

# Read-Only SQL Endpoint via Regex Validator

For low-stakes internal SQL escape hatches (Dashboard, MCP-tool, Companion-Service), a regex-based pre-check is a 95% solution that takes 5 minutes to implement. For high-stakes write-control, use a proper SQL parser.

## When to use

- Building a `/sql?q=<base64-SELECT>` endpoint for internal tools
- MCP-server tool that takes user-supplied SQL
- Dashboard query box that lets analysts run ad-hoc SELECTs
- Companion service that wants to expose raw query capability without full DB-credentials to the caller

## When NOT to use

- Write-allowed endpoints — never expose mutation via raw SQL; parameterize specific updates instead
- Public/Internet-facing endpoints — use a real SQL parser (sqlparse, pglast) and probably an SQL-permissions-restricted DB role
- Production trading systems where a malicious SELECT could affect performance (long table scan, `pg_sleep`, ...) — add timeout + query-cost budget on top
- Stored-procedure invocation that has side-effects despite being syntactically read-only

## The validator (Python, 30 lines)

```python
import re

def _is_readonly_sql(sql: str) -> bool:
    """Validate that SQL is read-only (SELECT/WITH/EXPLAIN only).

    Denies: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, CALL.
    Allows: SELECT, WITH (CTE), EXPLAIN, ANALYZE.

    Naive — catches obvious violations but not all corner cases.
    For high-stakes use, replace with sqlparse-based AST walk.
    """
    # Strip comments BEFORE matching — prevents comment-smuggle attacks
    sql_clean = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)
    # Normalize whitespace + uppercase
    sql_clean = re.sub(r"\s+", " ", sql_clean).strip().upper()

    denied = [
        r"^\s*INSERT\s", r"^\s*UPDATE\s", r"^\s*DELETE\s",
        r"^\s*DROP\s",   r"^\s*CREATE\s", r"^\s*ALTER\s",
        r"^\s*TRUNCATE\s", r"^\s*CALL\s",
    ]
    if any(re.search(p, sql_clean) for p in denied):
        return False
    allowed = [r"^SELECT\s", r"^WITH\s", r"^EXPLAIN\s", r"^ANALYZE\s"]
    return any(re.search(p, sql_clean) for p in allowed)
```

## Endpoint wrapper (FastAPI)

```python
@app.get("/sql")
async def sql_endpoint(q: str = Query(..., description="Base64-encoded read-only SQL")):
    try:
        sql = base64.b64decode(q).decode("utf-8")
    except Exception as e:
        return JSONResponse({"_error": "invalid_query_encoding", "detail": str(e)}, status_code=400)

    if not _is_readonly_sql(sql):
        return JSONResponse(
            {"_error": "forbidden_query", "detail": "Only SELECT/WITH/EXPLAIN allowed"},
            status_code=403,
        )

    pool = get_pool()
    if pool is None:
        return JSONResponse({"_error": "db_not_ready"}, status_code=503)
    try:
        rows = await pool.fetch(sql)
        return JSONResponse({
            "query": sql,
            "rows": [{k: _serialize_value(v) for k, v in dict(r).items()} for r in rows],
            "count": len(rows),
        })
    except asyncpg.PostgresError as e:
        return JSONResponse({"_error": "query_failed", "detail": str(e)}, status_code=400)
```

## Why base64-encode the SQL?

URL-safe transport for query-string params with special chars (quotes, semicolons, newlines). Caller does `echo "SELECT ..." | base64`, server decodes. Alternative: POST body — but GET is more cache-friendly and easier from `curl`.

## Defense layers (beyond the validator)

1. **DB-side**: dedicated read-only user/role with `GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user`. Even if the regex misses, the DB rejects.
2. **Network**: endpoint reachable only via Tailscale TLS-cert → already gates external attackers
3. **Audit-log**: every `/sql` call logged JSONL (timestamp + query-hash + caller-IP + outcome). Forensic trail for misuse.
4. **Timeout**: `pool.fetch(sql, timeout=10.0)` so a runaway query can't DoS the service.

## Test cases (Wolf 2026-06-11, 5 cases all passed)

```bash
# 1. Valid SELECT → 200
SQL=$(echo -n "SELECT count(*) FROM v3_trades" | base64)
curl /sql?q=$SQL  # → {"rows":[{"count":22}], ...}

# 2. Mutating UPDATE → 403
SQL=$(echo -n "UPDATE v3_trades SET closed_at=now()" | base64)
curl /sql?q=$SQL  # → 403 {"_error":"forbidden_query"}

# 3. Comment-smuggle attempt → 403
SQL=$(echo -n "--SELECT 1\nDELETE FROM v3_trades" | base64)
curl /sql?q=$SQL  # → 403 (comment stripped before matching)

# 4. WITH/CTE (allowed) → 200
SQL=$(echo -n "WITH x AS (SELECT 1 a) SELECT * FROM x" | base64)
curl /sql?q=$SQL  # → 200

# 5. Bad base64 → 400
curl /sql?q=INVALID  # → 400 {"_error":"invalid_query_encoding"}
```

## Anti-patterns

- ❌ **Skip comment-strip pre-pass**: caller smuggles `-- SELECT 1\nDELETE` and regex sees `SELECT` at line-start — passes naively. ALWAYS strip comments first.
- ❌ **Allow `EXECUTE`** in allowlist — `EXECUTE` runs prepared statements that can mutate. Deny it explicitly.
- ❌ **Trust the regex alone**: pair with a read-only DB-role. Defense-in-depth.
- ❌ **Forget `pg_sleep(...)` and `pg_terminate_backend(...)`**: technically SELECT but DoS-vector. For high-stakes endpoints, add SELECT-function-name denylist:
  ```python
  _DENY_FUNCTIONS = (r"pg_sleep", r"pg_terminate_backend", r"pg_cancel_backend",
                     r"pg_read_file", r"pg_ls_dir", r"dblink")
  for fn in _DENY_FUNCTIONS:
      if re.search(rf"\b{fn}\s*\(", sql_clean, re.IGNORECASE):
          return False
  ```
- ❌ **`SELECT … INTO new_table` bypassed allowlist**: `SELECT * INTO new_table FROM v3_trades` starts with SELECT but creates a table. Skill-Step 4 must explicitly check for `\bINTO\b` keyword after the prefix-match. Distinction: `INSERT INTO` is already denied; `SELECT INTO` needs separate handling.
- ❌ **`SELECT … FOR UPDATE` row-lock side-effect**: syntactically SELECT, semantically locks rows + can block other sessions. For trading-DB high-stakes: deny `\bFOR\s+(UPDATE|SHARE|NO\s+KEY\s+UPDATE|KEY\s+SHARE)\b`.
- ❌ **CTE-mutation via `RETURNING`**: `WITH x AS (INSERT INTO t VALUES (1) RETURNING id) SELECT * FROM x` — starts with WITH (allowed prefix), contains INSERT (denylist catches it). But also add **global `\bRETURNING\b` denylist** for safety because RETURNING outside CTE shouldn't appear in pure read queries anyway.
- ❌ **Multi-statement reject missing**: `SELECT 1; DELETE FROM v3_trades` could bypass if validator only checks first statement. Strip trailing `;` then reject if any `;` remains in body:
  ```python
  sql_trimmed = sql_clean.rstrip(";").strip()
  if ";" in sql_trimmed:
      return False  # multiple statements
  ```
- ❌ **Naive `--` comment-strip breaks string literals**: `SELECT 'a--b' AS x` becomes broken SQL after stripping. False-positive: legitimate query rejected. Edge-case acceptable for v1; production-grade needs `sqlparse` AST-walk.
- ❌ **Dollar-quoting `$$...$$` and `$tag$...$tag$` not handled**: PostgreSQL string literals using dollar-quoting can hide mutating keywords inside what looks like a "string". Regex won't see through. Production-grade needs AST.
- ❌ **Pass SQL via shell-interpolation in a subprocess** (e.g. `subprocess.run(["psql", "-c", sql])`): the shell can mis-quote and turn SQL into injection. Always use parameterized libraries (asyncpg, psycopg).
- ❌ **Audit-log the BASE64-encoded form only**: when forensics-time comes, you'll have to decode 500 lines manually. Log the decoded SQL (or both — encoded for round-trip, decoded for grep).

## Production-grade upgrade path

When the naive regex isn't enough (e.g. moving from internal dashboard to external API):
1. Replace `_is_readonly_sql` with `sqlparse.parse(sql)` AST walk that recursively confirms every statement-token is in {SELECT, WITH, EXPLAIN, ANALYZE}
2. Add `pglast` for full Postgres-AST awareness (handles every Postgres-specific edge case)
3. Move to a query-budget approach: estimate-via-EXPLAIN, reject if cost > threshold
4. Per-caller rate-limit + concurrent-query-quota

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS mit Polish)

- **RED-Subagent** (ohne Skill, Flask + psycopg2 für `POST /sql`): Schrieb umfangreichen Validator mit Multi-Layer-Defense (regex + `set_session(readonly=True)` + statement_timeout + read-only PG-Role). **Deckte selbst 7 Lücken im eigenen Code auf**: SELECT INTO bypass, dollar-quoting nicht behandelt, string-literal-mit-`--` false-positive, SELECT FOR UPDATE row-lock side-effect, CTE-RETURNING, identifier-collisions (`"drop"`-Spalte), unicode-whitespace. Sehr ehrlicher Self-Assessment.

- **GREEN-Subagent** (mit Skill via Read-Tool, gleiche Aufgabe): 4-Step-Pattern angewandt + zusätzlich Multi-Statement-Defense (Semikolon-Detection) + RETURNING-Denylist + Audit-Log mit decoded SQL. Identifizierte Skill-Adaption von FastAPI/asyncpg auf Flask/psycopg2 als trivial. Fand das EXECUTE-Anti-Pattern besonders wertvoll („klingt wie ‚Query ausführen', ist aber prepared-statement-Mutation").

- **Refactor angewendet vor PROMOTE** (basierend auf RED-Selbst-Befunden):
  - **Polish-1**: `pg_sleep/pg_terminate_backend` mit konkretem Code-Snippet als Function-Denylist
  - **Polish-2**: `SELECT INTO`-Bypass als eigenes Anti-Pattern dokumentiert (Skill-Step 4 muss `\bINTO\b` explizit prüfen)
  - **Polish-3**: `SELECT … FOR UPDATE` als Row-Lock-Side-Effect-Pattern hinzugefügt
  - **Polish-4**: Multi-Statement-Defense als eigenes Anti-Pattern mit Code-Snippet
  - **Polish-5**: `RETURNING`-Global-Denylist (nicht nur in CTE-Kontext)
  - **Polish-6**: Naive `--` Comment-Strip false-positive bei String-Literals als bekannte Edge-Case
  - **Polish-7**: Dollar-Quoting-Limitation als „needs AST" markiert

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Wirklicher sqlparse-AST-Walker** als production-grade Alternative dokumentieren mit Code-Beispiel
2. **Identifier-Kollisions**: bei DB mit reservierten-Wort-Spalten (`"drop"`, `"delete"`) — quoted-identifier-Detection erwähnen
3. **GROUP BY/ORDER BY edge-cases** mit Function-Calls (`ORDER BY pg_sleep(1)`) — function-denylist in vollem SQL nicht nur prefix
4. **Beispiel-DB-Role-Setup** mit konkretem SQL (`CREATE ROLE readonly_wolf WITH LOGIN PASSWORD '...'; GRANT pg_read_all_data TO readonly_wolf;`)
5. **Real-Use-Case-Test**: in next Stock3-MCP-Server oder Dashboard-Ad-hoc-Query anwenden

## Cross-Skill-Connections

- `subprocess-ssh-arg-quoting-via-shlex` (GA): sibling skill on argument-safety
- `enum-known-values-via-insert-grep` (GA): cross-table constants-set discovery
- `superpowers:writing-skills`: creating production-grade alternatives requires AST-walker pattern
