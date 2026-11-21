# ADR-0001: Adopt a domain-feature modular monolith

**Status:** Candidate for owner review. **Scope:** internal package layout only.

## Context
`airr/main.py` initially contained 207 lines of unrelated responsibilities: HTTP routes, HMAC authentication, validation schemas, transaction boundaries, approval decisions, health checks and correlation IDs. Workers and ORM entities were grouped by technical type. Learners cannot reliably map a feature to a file, and an agent can easily change an unrelated domain while fixing a bug.

## Decision
Use a **single FastAPI process with modular feature packages**: `requests`, `reviews`, `webhooks`, `health`, `classification`, `jobs`, `delivery` and `audit`. A short `app.py` wires routers and dependencies. All existing external API paths, status behavior, generated OpenAPI operation IDs, data tables, Alembic history and `airr.main:create_app` imports must remain compatible. Use explicit imports and data structures instead of a dependency injection framework or premature repository interfaces.

## Why not the alternatives?

- **One-file prototype:** quick initially, but difficult to maintain, test, and teach as behavior grows.
- **Only technical layers** (`routers/`, `services/`, `models/` across all features): workable for a small app, but navigation becomes expensive when there are many domains; grouping by business capability keeps related files nearby.
- **Microservices:** deployment, network, authentication, monitoring and transaction complexity would be disproportionate at this stage.
- **A full hexagonal/clean-architecture framework immediately:** likely unnecessary abstractions until actual external adapters and substitution requirements emerge.

## Consequences
Small, named files with clear test targets; API contract remains stable. Some compatibility facade imports are retained temporarily. Cross-feature dependencies still exist (e.g. approval creates a delivery record), and domain errors currently carry HTTP status metadata; this is a documented pragmatic compromise to revisit if new transports appear. Rewriting leases or idempotency here would add behavior changes and is deferred. Release remains blocked until PostgreSQL concurrency, security and commercial gates have separate evidence.

## Proof and rollback
Run existing tests and new architectural/OpenAPI tests before/after. A new private branch can be discarded without touching `main`. No database migration is authored because table/column definitions are unchanged. Record a before/after schema comparison when PostgreSQL is available.
