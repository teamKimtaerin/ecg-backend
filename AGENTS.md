# Repository Guidelines

## Project Structure & Module Organization
- `app/main.py` boots the FastAPI service and centralizes router registration.
- `app/api/v1/` contains versioned route modules (e.g., `admin.py`, `plugins.py`); keep related logic in `services/` and share schemas via `schemas/`.
- `app/db/` manages SQLAlchemy sessions, while migrations live in `alembic/` and seed data in `app/data/`.
- Support code sits in `scripts/` (ops helpers) and `docs/` (specs); tests belong in `tests/` with environment fixtures beside each suite.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create and activate a local virtual environment.
- `pip install -r requirements.txt`: install runtime, tooling, and security dependencies.
- `uvicorn app.main:app --reload`: run the API in development mode with live reload.
- `alembic upgrade head`: apply database migrations before exercising data paths.
- `pytest`: execute unit or async tests; add `-k pattern` to focus on modules.
- `ruff check app tests` and `black app tests`: lint and auto-format; run before committing.
- `mypy app`: enforce type coverage aligned with `mypy.ini`.

## Coding Style & Naming Conventions
- Use 4-space indentation and type hints on service boundaries; prefer dependency-injected functions over singletons.
- Modules, directories, and function names follow `snake_case`; classes remain `PascalCase`; constants use `UPPER_SNAKE_CASE`.
- Keep request/response models in `schemas/` and reuse DTOs to align with ML and plugin APIs.
- Let `black` and `isort` dictate formatting; rely on `ruff` for quick lint fixes (`ruff check --fix` when safe).

## Testing Guidelines
- Extend `tests/` with `test_<feature>.py` files mirroring the `app/` layout; parametrize to cover async branches.
- Use `pytest-asyncio` for coroutine handlers and `httpx.AsyncClient` against `app.main.app`.
- Include fixtures for temporary AWS/S3 credentials or database overlays under `tests/conftest.py`.
- Target meaningful coverage for DB migrations and service integrations before requesting review.

## Commit & Pull Request Guidelines
- Follow the `Type: Summary` convention seen in history (`Feat: ...`, `Fix: ...`, `🤖 Auto-fix: ...`) using imperative verbs.
- Reference Jira/issue IDs when applicable and keep the body wrapped at ~100 columns.
- Each PR should explain What/Why/How, list manual checks, and attach API traces or sample payloads when changing external contracts.
- Request reviewers early, link related docs (e.g., `ARCHITECTURE.md`), and confirm `ruff`, `black`, `mypy`, and `pytest` all pass.
