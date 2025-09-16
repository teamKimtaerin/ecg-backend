# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ECG Backend is a FastAPI application that provides video processing and caption generation services. The project integrates AWS S3 for file storage, PostgreSQL for data persistence, Google OAuth authentication, and communicates with ML analysis servers for video processing. The application supports real-time project management with synchronization capabilities and includes automated PR generation workflows.

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

# Run linting and type checking manually
ruff check . --fix
black --check .
mypy . --ignore-missing-imports
bandit -r .

# Run tests (currently no test suite configured)
pytest --maxfail=1 --disable-warnings -q || echo "No tests found"

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

### PR Generation Workflow
```bash
# Automated PR creation with Claude AI integration
./.claude/scripts/prm "Feature description"

# This script will:
# - Validate Git state and staged files
# - Auto-generate commit messages
# - Create Claude-optimized prompts for PR descriptions
# - Generate GitHub PR with structured format
```

### Code Quality Tools
- **Black**: Code formatting (automatically applied via pre-commit)
- **Ruff**: Fast linting with auto-fix capabilities  
- **MyPy**: Static type checking with missing imports ignored
- **Bandit**: Security vulnerability scanning
- **Pytest**: Test execution framework (no tests currently configured)

## Architecture

### Core Structure
```
app/
├── main.py                 # FastAPI app entry point with CORS and middleware
├── core/config.py          # Centralized settings using Pydantic BaseSettings
├── api/v1/                 # Versioned API endpoints
│   ├── routers.py         # Router registration  
│   ├── auth.py            # OAuth authentication endpoints
│   ├── ml_video.py        # ML server integration for video processing
│   ├── video.py           # Direct video upload endpoints
│   └── projects.py        # Project and clip management endpoints
├── models/                # SQLAlchemy database models
│   ├── user.py            # User authentication model
│   ├── job.py             # Video processing job tracking
│   ├── project.py         # Caption project with synchronization
│   ├── clip.py            # Video clip segments with timing
│   └── word.py            # Individual word-level captions
├── schemas/               # Pydantic request/response schemas
├── services/              # Business logic layer
│   ├── auth_service.py    # Authentication business logic
│   ├── s3_service.py      # AWS S3 integration
│   ├── job_service.py     # Video processing job management
│   └── project_service.py # Project synchronization logic
└── db/                    # Database configuration and initialization
    ├── database.py        # SQLAlchemy engine and session management
    ├── init_db.py         # Database initialization with auto table creation
    └── seed_data.py       # Development seed data
```

### Key Integrations
- **Database**: PostgreSQL with SQLAlchemy ORM and automatic initialization
- **Authentication**: Google OAuth with JWT tokens and session management
- **File Storage**: AWS S3 with presigned URLs for secure file access  
- **ML Processing**: Async communication with external ML servers for video analysis
- **Real-time Sync**: Project synchronization with version control and conflict resolution
- **API Documentation**: Auto-generated at `/docs` (Swagger) and `/redoc`

### Environment Configuration
Critical environment variables (see app/core/config.py):
- **Database**: PostgreSQL connection settings with Docker Compose defaults
- **AWS S3**: Access keys, bucket name, region, and presigned URL expiration
- **Google OAuth**: Client ID, client secret, and redirect URI
- **JWT**: Secret keys and token expiration settings
- **CORS**: Frontend URL allowlist for cross-origin requests
- **ML Servers**: Both `MODEL_SERVER_URL` and `ml_api_server_url` for video processing
- **Debug/Mode**: Development vs production behavior flags

### Video Processing Architecture
- **Async ML Integration**: Video processing requests sent to external ML servers
- **Job-based Workflow**: Track processing status with unique job IDs  
- **Callback Pattern**: ML servers POST results back to `/api/v1/ml-results`
- **S3 Integration**: Secure file upload/download with presigned URLs
- **Progress Tracking**: Real-time status updates during video analysis

### Project Management System
- **Real-time Collaboration**: Multi-user project editing with conflict resolution
- **Version Control**: Project versioning with change tracking and sync status
- **Hierarchical Structure**: Projects → Clips → Words with timing information
- **JSON Storage**: Flexible schema using PostgreSQL JSON columns for dynamic data

### Database Architecture
- **Auto-initialization**: Tables created from SQLAlchemy models on startup (conditional)
- **Relationship Mapping**: User → Projects → Clips → Words with foreign key constraints  
- **Seed Data**: Development users created automatically with validation
- **Session Management**: Proper cleanup with dependency injection pattern

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

### Development Automation

#### CI/CD Pipeline (.github/workflows/ci.yml)
Automated quality checks on push/PR to main/dev branches:
- **Code formatting**: Black verification
- **Linting**: Ruff with auto-fix capabilities
- **Type checking**: MyPy with missing imports ignored  
- **Security**: Bandit vulnerability scanning
- **Testing**: Pytest (currently no test suite)

#### PR Generation Workflow (.claude/scripts/prm)
Automated PR creation with Claude AI integration:
- **Git Validation**: Ensures proper branch and staged files
- **Smart Commits**: Auto-generated commit messages with co-author attribution
- **AI Integration**: Structured prompts for Claude Code to generate PR descriptions
- **GitHub CLI**: Automatic PR creation with base branch detection

### Configuration Management

#### Startup Behavior (app/main.py)
- **Conditional DB Init**: Only initializes database for non-default URLs
- **Session Middleware**: Required for OAuth state management
- **CORS Configuration**: Environment-based origin allowlist
- **Health Endpoints**: `/health` and `/` for monitoring

#### Pre-commit Integration (.pre-commit-config.yaml)
Automatic code quality enforcement before commits:
- **Black**: Code formatting
- **Ruff**: Linting with auto-fixes
- **MyPy**: Type checking
- **Bandit**: Security scanning
- **Python 3.11**: Target version for all tools

## Important Implementation Notes

### ML Server Communication Pattern
```python
# app/api/v1/ml_video.py - Async video processing workflow
1. Client uploads video → Generate S3 presigned URL
2. ML server processes video → Updates job status via callbacks
3. Results stored in database → Client polls for completion
4. Error handling with job status tracking throughout
```

### Project Synchronization Logic
The project system supports real-time collaboration:
- **Version Control**: Tracks changes with timestamps and change counters
- **Sync Status**: pending → syncing → synced → failed states
- **Conflict Resolution**: Server-side merging of concurrent edits
- **JSON Schema**: Flexible clip and settings storage using PostgreSQL JSON
