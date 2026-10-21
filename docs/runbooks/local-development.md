# Local development runbook

1. Copy `backend/.env.example` to `backend/.env` and obtain values through the approved secret process.
2. From `backend/`, install with `python -m pip install -e ".[dev]"`.
3. Run `python -m pytest` and `python -m ruff check app tests alembic`.
4. Start local services with `docker compose up --build` only after all required environment values are set.
5. On a failed migration, stop the API, inspect the Alembic revision and MySQL logs, then use the documented downgrade only after confirming the target database.

Never commit `.env`, tokens, password hashes, or production data.
