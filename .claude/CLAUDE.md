# CLAUDE.md!

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the backend for an Expressive Caption Generator application built with FastAPI. The project integrates authentication, database management, and is designed to work with ML servers for audio/video processing and analysis.

## Commands

### Development Server

```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Start on specific port (default is 8000)
uvicorn app.main:app --reload --port 8080
```

### Docker Development

```bash
# Start with Docker Compose (PostgreSQL + Backend)
docker-compose up

# Build for development
docker build --target dev --build-arg MODE=dev -t ecg-backend:dev .

# Build for production
docker build --target prod --build-arg MODE=prod -t ecg-backend:prod .
```

### Code Quality Tools

```bash
# Format code with Black
python -m black app/

# Run linting with Ruff
python -m ruff check app/ --fix

# Type checking with MyPy
python -m mypy app/ --ignore-missing-imports

# Security check with Bandit
python -m bandit -r app/

# Run tests
pytest --maxfail=1 --disable-warnings -q
```

### Database Management

```bash
# Database will auto-initialize on FastAPI startup
# To manually run database initialization:
python -c "from app.db.init_db import init_database; init_database()"

# To create seed data only:
python -c "from app.db.seed_data import create_seed_data; create_seed_data()"
```

### Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Then edit .env with actual values
```

## Architecture

### Core Application Structure

- **app/main.py**: FastAPI application entry point with startup events for database initialization
- **app/core/config.py**: Environment configuration management using Pydantic Settings
- **app/db/**: Database management layer
  - **database.py**: SQLAlchemy engine, session management, and dependency injection
  - **init_db.py**: Automatic database initialization (table creation + seed data)
  - **seed_data.py**: Development seed data for testing (includes OAuth users)

### Authentication System

- **Dual authentication**: Local email/password + Google OAuth 2.0
- **JWT-based**: Bearer token authentication with configurable expiration
- **Models**: User model supports both local and OAuth providers
- **Services**: Centralized authentication logic in `auth_service.py`
- **Session management**: Required for OAuth state handling

### API Layer (Versioned)

- **app/api/v1/**: Version 1 API endpoints
  - **auth.py**: Authentication endpoints (signup, login, OAuth flows)
  - **routers.py**: Router registration and configuration
- **Auto-documentation**: Available at `/docs` (Swagger) and `/redoc`

### Key Technologies

- **FastAPI**: Web framework with automatic OpenAPI generation
- **SQLAlchemy 2.0**: Modern ORM with async support potential
- **PostgreSQL**: Primary database with Docker Compose setup
- **JWT + OAuth 2.0**: Authentication with Google integration
- **Authlib**: OAuth client implementation
- **Pydantic**: Data validation and settings management
- **Docker**: Multi-stage builds (dev/prod) with health checks

### Database Architecture

- **Auto-initialization**: Tables created from SQLAlchemy models on startup
- **Seed data**: Automatic test user creation for development
- **Connection pooling**: Configured for production scalability
- **Health checks**: Database connectivity monitoring in Docker

### CI/CD Pipeline

- **GitHub Actions**: Automated testing on push/PR to main/dev branches
- **Quality gates**: Black, Ruff, MyPy, Bandit, pytest
- **Branch protection**: Configured to require status checks before merge

## Important Configuration

### Environment Variables (.env file)

- **Database**: PostgreSQL connection settings (Docker Compose or external)
- **Authentication**: JWT secrets and Google OAuth credentials
- **AWS S3**: File storage configuration (access keys, bucket, region)
- **CORS**: Frontend URL allowlist
- **Debug/Mode**: Development vs production behavior

### Authentication Flow

1. **Local Auth**: Email/password → JWT token → Bearer authentication
2. **OAuth Flow**: Google login → user creation/login → JWT token
3. **Token Usage**: Include `Authorization: Bearer <token>` header in requests

### Development Workflow

1. **Database**: Automatically initializes on `docker-compose up` or FastAPI startup
2. **Seed users**: Test accounts created automatically (see `seed_data.py`)
3. **API Testing**: Use `/docs` for interactive testing with authentication
4. **Pre-commit hooks**: Code quality checks before commits (optional)

### ML Server Integration Design

The backend is designed to communicate with separate ML analysis servers:

- **Job-based processing**: Send video processing requests with S3 file keys
- **Callback pattern**: ML servers POST results back to `/api/v1/ml-results`
- **Async workflow**: Non-blocking video processing with status tracking
