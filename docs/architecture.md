# AI Request Router — Modular monolith architecture (candidate)

This is a **single deployable service**, not microservices. Organize around *why code changes*, while keeping explicit HTTP/domain/persistence boundaries. This refactor changes Python structure only: it does **not** change database tables, introduce migrations, enable LLM mode, enable outbound HTTP, or authorize deployment.

## Package map

```text
product/src/airr/
  app.py                     # composition root: wire dependencies + routers
  asgi.py                    # uvicorn import target
  main.py                    # compatibility import for create_app
  config.py                  # validated environment settings
  db.py                      # SQLAlchemy engine, session factory and Base
  models.py                  # compatibility imports; not new model definitions
  worker.py                  # compatibility CLI for workers
  classifier.py              # compatibility deterministic classifier import
  core/
    dependencies.py          # FastAPI adapters: session/settings/auth keys
    errors.py                # HTTP exception serialization
    problem.py               # application error contract
    observability.py         # correlation id and early size response
    identifiers.py           # UTC timestamps and UUIDs
  modules/
    health/router.py         # /health/live and /health/ready
    requests/{models,schemas,serialization,service,router}.py
    reviews/{schemas,service,router}.py
    webhooks/router.py       # HMAC-authenticated HTTP adapter
    jobs/{models,claims}.py  # durable job and lease acquisition
    classification/{rules,worker}.py
    delivery/{models,worker}.py
    audit/models.py
    sources/{models,service}.py # private operator-managed API keys
```

`router.py` defines HTTP paths and dependencies; `schemas.py` defines validation; `service.py` owns a use case and transaction; `models.py` owns database entities. Not every feature needs all four files: add a file when it has a clear responsibility and tests. Shared domain models are imported explicitly; `airr.models` remains only a compatibility surface for migrations and older consumers.

## Call flows and error boundaries

**HTTP intake**: `app.create_app` → `requests.router.intake` → `core.dependencies.auth_source` → `requests.schemas.Intake` → `requests.service.create_request` → `Request + Job + AuditEvent` *one transaction* → HTTP 202 after commit. On duplicate external ID with different payload, 409; on database failure, 503.

**Webhook intake**: `webhooks.router.signed_webhook` → HMAC verification → `Intake` → SAME request service. Do not duplicate persistence logic in the webhook.

**Classification**: `worker.py` (CLI compatibility) → `classification.worker.process_classification_once` → `jobs.claims.claim_next` → `classification.rules.classify` → version/state update + audit. Background worker is a separate process in production. PostgreSQL leasing/fencing is **not** yet verified.

**Reviewer**: `reviews.router` → `auth_reviewer` → `reviews.service` → conditional DB update by status/version → delivery record + audit. Internal delivery only.

**Health**: `health.router` checks HTTP liveness independently; readiness checks the configured database and `requests` table. `core.observability` returns `X-Trace-Id` even on early 413.

## Dependency rules

1. `app.py` may import adapters/routes. Routes may import services/schemas and core dependencies.
2. Services, workers, ORM models and deterministic rules MUST NOT import FastAPI/Starlette, directly access `Request.app`, or return `Response` objects; they accept plain data and session factories.
3. Domain modules MUST NOT import `airr.main` or `airr.app` (no circular imports); `models.py`, `main.py`, `worker.py` are compatibility facades only.
4. Do not put database transactions in route handlers. All `with sf.begin()` operations must be in services/workers, and a transaction must either complete all intended effects or roll back.
5. Never define the same ORM table twice; Alembic imports `airr.models` to register all entities once.
6. Follow existing API/OpenAPI response contracts, operation IDs, error codes, authentication and HMAC semantics across refactors. Preserve tests before and after moving code.
7. Optional external sends/LLM providers must use explicit ports/adapters and be disabled until separately reviewed. Do not use microservices, a generic dependency injection container, or an abstract repository class without an actual use case.
8. Avoid files larger than 120 executable lines without documenting a reason. Line count is a review trigger, not an excuse to split tightly coupled logic into meaningless files.
9. Keep public code and safe documentation inside `product/`; tests, agent instructions and learner answers remain private. Private GitHub development repository **must never be made public** after internal material enters its history.

## Verification

From repository root with dependencies installed and `AIRR_PUBLIC_SOURCE_DIR` set to `product`:

```sh
python -m pytest -c private-qa/pytest.ini private-qa/tests private-qa/test_migration.py -q
python private-agent/modular-project-engineer/scripts/check_boundaries.py --package product/src/airr
python private-qa/run_http_smoke.py
```

These commands check API regressions, static structural boundaries, migrations and local HTTP smoke. Live PostgreSQL integration, concurrent job fencing, production deployment, rate limits, UI authentication and external sends are **separate, pending acceptance gates**.

## Day 2 candidate: provisioned source credentials

The existing `AIRR_SOURCE_KEY` remains a compatibility-only default identity (`source_id=default`).
Operator-provisioned sources are stored in `sources`, with a unique SHA-256 digest
of a server-generated 256-bit random credential, an enabled flag and timestamps.
The digest is appropriate for these random credentials, not a password hash for
user-chosen passwords. The plaintext key is displayed only once by the
**local-only** `python -m airr.source_admin create SOURCE_ID` command. The
operator may rotate or disable the credential using the same CLI, not an HTTP
endpoint. Never copy output into source control or shared logs.

`core.dependencies.auth_source` authenticates the legacy default credential or
looks up a provisioned source. The `requests` endpoint passes the authenticated
source ID to `requests.service.create_request`, which checks and stores
`(source_id, external_id)` atomically under the existing unique constraint.
A disabled source returns HTTP 403; unknown credentials return 401. The
reviewer key remains separate. The signed webhook reads request body chunks with a strict byte cap before
HMAC verification; it still uses only the default
environment signing secret and `source_id=default` at this stage; per-source
webhook keys/replay nonce enforcement are **not implemented**.

The `requests.source_id` column does not yet carry a foreign key to `sources`
because the legacy environment-only `default` identity has no row there.
Design and migration of that relationship require a separate compatibility
review before turning off the legacy key.

SQLite engine setup now recognizes both `sqlite:` and `sqlite+pysqlite:`
URLs and enables `PRAGMA foreign_keys=ON` for each fresh DBAPI connection.
Live PostgreSQL migration and duplicate-race tests are still pending.
