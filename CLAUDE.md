# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ECG Backend is a FastAPI application for Expressive Caption Generation that provides video processing and user authentication services. The project integrates with AWS S3 for file storage, PostgreSQL for data persistence, and includes OAuth authentication through Google. It's designed to work with ML servers for audio/video processing and analysis using Whisper models. The application is containerized with Docker and includes comprehensive CI/CD workflows.

## Development Commands

### Local Development
```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Start on specific port (default is 8000)
uvicorn app.main:app --reload --port 8080

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Then edit .env with actual values
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

# Set up pre-commit hooks (run once)
./setup-pre-commit.sh
```

### Database Management
```bash
# Database will auto-initialize on FastAPI startup
# To manually run database initialization:
python -c "from app.db.init_db import init_database; init_database()"

# To create seed data only:
python -c "from app.db.seed_data import create_seed_data; create_seed_data()"

# Manual Jobs table creation for production:
python create_jobs_table.py
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

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Core Application Structure
- **app/main.py**: FastAPI application entry point with startup events for database initialization
- **app/core/config.py**: Environment configuration management using Pydantic Settings (line 8-70)
- **app/db/**: Database management layer
  - **database.py**: SQLAlchemy engine, session management, and dependency injection
  - **init_db.py**: Automatic database initialization (table creation + seed data)
  - **seed_data.py**: Development seed data for testing (includes OAuth users)

### API Layer (Versioned)
- **app/api/v1/**: Version 1 API endpoints
  - **auth.py**: Authentication endpoints (signup, login, OAuth flows)
  - **video.py**: Video processing endpoints
  - **ml_video.py**: ML server integration endpoints
  - **routers.py**: Router registration and configuration
- **Auto-documentation**: Available at `/docs` (Swagger) and `/redoc`

### Authentication System
- **Dual authentication**: Local email/password + Google OAuth 2.0
- **JWT-based**: Bearer token authentication with configurable expiration (1440 minutes default)
- **Models**: User model supports both local and OAuth providers
- **Services**: Centralized authentication logic in `auth_service.py`
- **Session management**: Required for OAuth state handling

### ML Server Integration Architecture
The backend is designed to communicate with separate ML analysis servers:
- **Job-based processing**: Send video processing requests with S3 file keys using Job model
- **Callback pattern**: ML servers POST results back to `/api/upload-video/result`
- **Async workflow**: Non-blocking video processing with status tracking
- **S3 Integration**: Uses presigned URLs for secure video upload and access
- **Status tracking**: Jobs table with UUID primary keys and JSONB result storage

### Key Technologies
- **FastAPI**: Web framework with automatic OpenAPI generation
- **SQLAlchemy 2.0**: Modern ORM with async support potential
- **PostgreSQL**: Primary database with Docker Compose setup
- **JWT + OAuth 2.0**: Authentication with Google integration via Authlib
- **Pydantic**: Data validation and settings management
- **Docker**: Multi-stage builds (dev/prod) with health checks
- **AWS S3**: File storage with presigned URL generation

### Database Architecture
- **Auto-initialization**: Tables created from SQLAlchemy models on startup (app/main.py:16-37)
- **Conditional init**: Only initializes if not using default local database URL
- **Jobs table**: UUID-based job tracking with JSONB results and status indexing
- **Seed data**: Automatic test user creation for development
- **Connection pooling**: Configured for production scalability
- **Health checks**: Database connectivity monitoring in Docker

### Environment Configuration
Critical environment variables (see app/core/config.py):
- **Database**: PostgreSQL connection settings (Docker Compose or external RDS)
- **AWS**: S3 credentials, bucket name, region (ap-northeast-2 default)
- **Authentication**: JWT secrets and Google OAuth credentials
- **ML Server**: MODEL_SERVER_URL for video processing integration
- **CORS**: Frontend URL allowlist
- **Debug/Mode**: Development vs production behavior

### CI/CD Pipeline
- **GitHub Actions**: Automated testing on push/PR to main/dev branches (.github/workflows/ci.yml)
- **Quality gates**: Black, Ruff, MyPy, Bandit, pytest with early termination
- **Branch protection**: Configured to require status checks before merge
- **Auto-fix workflow**: Separate workflow for automated code formatting

### Pre-commit Integration
Automatic code quality enforcement before commits (.pre-commit-config.yaml):
- **Black**: Code formatting (Python 3.11)
- **Ruff**: Linting with auto-fix and formatting
- **MyPy**: Type checking with missing imports ignored
- **Additional dependencies**: types-all for comprehensive type checking

### Development Workflow
1. **Database**: Automatically initializes on `docker-compose up` or FastAPI startup
2. **Seed users**: Test accounts created automatically (see `seed_data.py`)
3. **API Testing**: Use `/docs` for interactive testing with authentication
4. **Pre-commit hooks**: Code quality checks before commits (./setup-pre-commit.sh)

### Authentication Flow
1. **Local Auth**: Email/password → JWT token → Bearer authentication
2. **OAuth Flow**: Google login → user creation/login → JWT token
3. **Token Usage**: Include `Authorization: Bearer <token>` header in requests