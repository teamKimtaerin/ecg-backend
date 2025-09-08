# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ECG Backend is a FastAPI application that provides video processing and user authentication services. The project integrates with AWS S3 for file storage, PostgreSQL for data persistence, and includes OAuth authentication through Google. The application is containerized with Docker and includes comprehensive CI/CD workflows.

## Development Commands

### Local Development
```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks (run once)
./setup-pre-commit.sh

# Run linting and type checking manually
ruff check .
black --check .
mypy .
bandit -r .

# Run tests
pytest --maxfail=1 --disable-warnings
```

### Database Operations
```bash
# Database initialization happens automatically on startup
# Check app/db/init_db.py for database setup and seed data
```

### Docker Development
```bash
# Build and run development environment
docker-compose up --build

# Build development image only
docker build --target dev --build-arg MODE=dev -t ecg-backend:dev .

# Build production image
docker build --target prod --build-arg MODE=prod -t ecg-backend:prod .
```

### Code Quality Tools
- **Black**: Code formatting (automatically applied via pre-commit)
- **Ruff**: Fast linting with auto-fix capabilities
- **MyPy**: Static type checking with missing imports ignored
- **Bandit**: Security vulnerability scanning
- **Pytest**: Test execution framework

## Architecture

### Core Structure
```
app/
├── main.py                 # FastAPI app entry point with CORS and middleware
├── core/config.py          # Centralized settings using Pydantic BaseSettings
├── api/v1/                 # Versioned API endpoints
│   ├── routers.py         # Router registration
│   ├── auth.py            # OAuth authentication endpoints
│   ├── video.py           # Video processing endpoints
│   └── endpoints/         # Additional API endpoints
├── models/                # SQLAlchemy database models
├── schemas/               # Pydantic request/response schemas
├── services/              # Business logic layer
│   ├── auth_service.py    # Authentication business logic
│   └── s3_service.py      # AWS S3 integration
└── db/                    # Database configuration and initialization
    ├── database.py        # SQLAlchemy engine and session management
    ├── init_db.py         # Database initialization with auto table creation
    └── seed_data.py       # Development seed data
```

### Key Integrations
- **Database**: PostgreSQL with SQLAlchemy ORM and automatic initialization
- **Authentication**: Google OAuth with JWT tokens and session management
- **File Storage**: AWS S3 with presigned URLs for secure file access
- **API Documentation**: Auto-generated at `/docs` (Swagger) and `/redoc`

### Environment Configuration
Critical environment variables (see app/core/config.py:8-68):
- Database connection settings with defaults for local development
- AWS credentials for S3 integration
- Google OAuth client configuration
- JWT secret keys and token expiration settings
- CORS origins configuration
- Model server URL for video processing

### Database Architecture
- Automatic table creation and seeding on startup via app/main.py:16-29
- SQLAlchemy models with relationship mapping
- Session management with proper cleanup
- Development seed data for testing

### Docker Configuration
- Multi-stage Dockerfile with dev/prod targets
- Docker Compose with PostgreSQL service and health checks
- Volume mounting for development hot-reload
- Environment variable injection from .env files

### CI/CD Pipeline
The project includes automated quality checks on push/PR:
- Code formatting verification (Black)
- Linting and auto-fixes (Ruff)
- Type checking (MyPy)
- Security scanning (Bandit)
- Test execution with early termination on failure

### Pre-commit Integration
Automatic code quality enforcement before commits:
- Black formatting
- Ruff linting with fixes
- MyPy type checking
- Configured for Python 3.11