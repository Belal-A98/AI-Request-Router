# AI Request Router (early engineering slice)

**Status: development preview, NOT ready for public deployment or sale.**

This is a real, test-driven FastAPI backend for authenticated JSON/Webhook request intake with SQL persistence, deterministic classification, a reviewer approval API, audit trail, and internal-only delivery. It is an *approval-first integration foundation*, not a complete AI product yet.

### Verified behavior (SQLite)

- Authenticated JSON intake, signed webhook using HMAC-SHA256 with a 5-minute timestamp window.
- Canonical payload hash + unique `(source_id, external_id)` to avoid duplicate requests/jobs. Payload mismatch returns 409.
- `202 Accepted` after the database transaction commits.
- Persistent classification jobs; local deterministic four-category rules (`sales`, `support`, `billing`, `other`).
- Reviewer-only read/list, version-guarded approval/rejection, internal-only delivery worker, metadata-only audit events.
- A public SQLite regression suite is included in `tests/`. Further PostgreSQL concurrency and security testing are required before production deployment.

### IMPORTANT limitations

- `rules` mode is not an LLM; **no live AI integration has been verified**.
- Outbound HTTP/Webhooks and external automatic sends are **not implemented**, by design. Internal delivery only.
- Human authentication uses a separate reviewer API secret, **not** browser session login; deploy only behind trusted local/private access. Admin UI, CSRF protection, rate limiting and full permissions still pending.
- PostgreSQL-specific concurrency and transaction tests are **not yet run**. SQLite tests cannot establish PostgreSQL correctness.
- Schema migration tooling is present, but production rollback/backups, secret rotation and security assessment require further validation.
- Not a multi-tenant SaaS. The source code is distributed under the MIT License; production deployment still requires independent hardening and validation.

## Local SQLite setup

Requires Python 3.12+ and a virtual environment.

```bash
python -m venv .venv
# Activate .venv as appropriate to your OS
pip install -e .
```

Set environment variables for your shell (do NOT paste working secrets into GitHub):

```bash
export AIRR_SOURCE_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export AIRR_REVIEWER_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DATABASE_URL="sqlite+pysqlite:///./airr.sqlite"
export AIRR_CLASSIFIER_MODE="rules"
```

On Windows PowerShell, generate each value with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, then assign it to `$env:AIRR_SOURCE_KEY` etc. Set `$env:DATABASE_URL="sqlite+pysqlite:///./airr.sqlite"`.

Run migrations and server:

```bash
alembic upgrade head
uvicorn airr.asgi:app --host 127.0.0.1 --port 8000
```

`GET /docs` displays OpenAPI. `/health/live` and `/health/ready` are probe endpoints. The source API expects `X-Source-Key`; reviewer APIs expect the distinct `X-Reviewer-Key`.

### Minimal flow (synthetic payload only)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/requests \
  -H "Content-Type: application/json" -H "X-Source-Key: $AIRR_SOURCE_KEY" \
  -d '{"external_id":"demo-1","subject":"Need invoice","message":"Please help with invoice"}'
python -m airr.worker classify
# GET /api/v1/requests/{request_id} with X-Reviewer-Key to read version
# POST /api/v1/requests/{request_id}/approve with {"expected_version":1,"category":"billing","priority":"normal"}
python -m airr.worker deliver
```

### Local PostgreSQL with Docker (not tested in this execution environment)

1. Install Docker Desktop + Compose and verify available memory and ports.
2. Copy `.env.example` to `.env`, replace both generated secrets, and add `AIRR_DB_PASSWORD` with a newly generated password. The Compose file binds PostgreSQL and API to `127.0.0.1` only.
3. `docker compose -f compose.postgres.yaml up -d db`
4. `docker compose -f compose.postgres.yaml run --rm api alembic upgrade head`
5. `docker compose -f compose.postgres.yaml up -d api`
6. `docker compose -f compose.postgres.yaml --profile manual-worker run --rm worker python -m airr.worker classify`
7. Repeat with `deliver` after a reviewer approval.
8. Run **private** QA from the separate test bundle against real PostgreSQL; do not call it verified until tests pass and logs are examined.

### Source privacy

The code is public. **Do not commit** any local `.env`, customer data, private test source, learning notes, agent prompts, execution logs, evaluation rubrics or private build packet. `.gitignore` does not erase history. Keep private QA and training directories as siblings outside the checkout.

### Future milestones

Provider-backed LLM classification, authenticated admin UI, safe external webhook/SSRF guard, delivery unknown-state reconciliation, PostgreSQL tests, backup/restore drills, independent security review, approved public demo. These are planned, not delivered.

### Code navigation (modular architecture)

Start with [`docs/architecture.md`](docs/architecture.md) and [`docs/adr/0001-modular-monolith.md`](docs/adr/0001-modular-monolith.md). `src/airr/app.py` wires dependency adapters and domain routers; `main.py` is a stable compatibility entrypoint. Core operations are located by feature (`modules/requests`, `modules/reviews`, `modules/health`, `modules/webhooks`, `modules/jobs`, `modules/classification`, `modules/delivery`). Keep private test source and personal training records outside any future public release.

## Day 2: additional source credentials (private candidate)

After running the versioned Alembic migrations, a trusted local operator can
provision an API source. These are local CLI operations, not HTTP endpoints:

```sh
python -m airr.source_admin create vendor_one
python -m airr.source_admin rotate vendor_one
python -m airr.source_admin disable vendor_one
python -m airr.source_admin enable vendor_one
```

Creation/rotation prints a newly generated high-entropy `NEW_SOURCE_KEY` once.
Capture it in an appropriate secret manager and do not copy it to shell command
arguments, CI logs, source control, or screenshots. Send the key via
`X-Source-Key` to `POST /api/v1/requests`. Each source has an independent
namespace for `external_id` idempotency. The legacy environment key remains
valid for the default source until an explicit migration removes it.

Signed webhook ingestion remains tied to the legacy default secret;
source-specific webhook signing and dedicated anti-replay tokens are not yet
implemented. Real PostgreSQL concurrency and production readiness remain unverified.

## Day 2: reviewer query filters

Reviewer-authorized `GET /api/v1/requests` supports optional `status`, `category`, `limit`, and `offset` query parameters. `category` accepts `sales`, `support`, `billing`, or `other`. Unsupported categories return `422` with `error.code=INVALID_INPUT`, a response `trace_id`, and a matching `X-Trace-Id` header. Filters are combined before deterministic ordering and pagination. Source API credentials cannot read reviewer listings. These endpoints are development-preview functionality, not a public deployment authorization.

## Quality checks

Install the test dependencies in a fresh virtual environment and run the public regression suite:

```bash
pip install -e '.[test]'
python -m pytest tests -q
python -m compileall -q src
```

These tests use synthetic, isolated SQLite files. Their presence does **not** imply that hosted CI, PostgreSQL concurrency tests, penetration testing, or production hardening have been completed. Production deployment is out of scope for this development preview.
