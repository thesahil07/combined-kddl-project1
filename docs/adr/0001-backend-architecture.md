# ADR 0001: Backend architecture

## Decision

Use Python, FastAPI, SQLAlchemy, MySQL 8, and four-layer Clean Architecture.

## Consequences

Presentation routes depend only on application/domain code; infrastructure is
wired through `presentation/api/dependencies.py`. Repository contracts are in
the domain layer and SQL implementations remain in infrastructure.
