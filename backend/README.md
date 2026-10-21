# KDDL Dials Talent Transformation Platform Backend

## Architecture

This repository is the backend root and follows Clean Architecture:

- `app/domain/` — entities, exceptions, interfaces, and value objects.
- `app/application/` — DTOs, use cases, and application services.
- `app/infrastructure/` — database, repositories, security, and external-service adapters.
- `app/presentation/` — FastAPI routes, dependency wiring, and middleware.

## Local setup

Copy `.env.example` to `.env` and set the required values through your approved
secret-management process. Never commit the resulting `.env` file or place
real credentials in Compose/source files. Then install with:

```powershell
python -m pip install -e ".[dev]"
```

Run tests with `python -m pytest`. For local MySQL/API startup, run `docker compose up --build`.

## Fictional demo data

After applying migrations to a local database, seed the platform with safe,
fictional demo users and employees. The password is supplied at runtime and is
never saved in source control:

```powershell
$env:DEMO_SEED_PASSWORD='choose-a-local-demo-password'
python scripts/seed_demo_data.py
```

The seeder is idempotent. It adds six accounts covering the fixed roles and a
small fictional org structure; do not use it against a production database.

Architecture decisions live in `/docs/adr`; local operational steps are in
`/docs/runbooks/local-development.md`.
