# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ECG Backend is a FastAPI application that provides video processing and caption generation services. The project integrates AWS S3 for file storage, PostgreSQL for data persistence, Google OAuth authentication, and communicates with ML analysis servers for video processing. The application supports real-time project management with synchronization capabilities and includes automated PR generation workflows.

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
ruff check . --fix
black --check .
mypy . --ignore-missing-imports
bandit -r .

# Run tests (currently no test suite configured)
pytest --maxfail=1 --disable-warnings -q || echo "No tests found"
```

### Database Operations
```bash
# Database initialization happens automatically on startup
# Manual database initialization (if needed)
python -c "from app.db.init_db import init_database; init_database()"

# Create seed data only
python -c "from app.db.seed_data import create_seed_data; create_seed_data()"
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

### Docker Configuration
- Multi-stage Dockerfile with dev/prod targets
- Docker Compose with PostgreSQL service and health checks
- Volume mounting for development hot-reload
- Environment variable injection from .env files

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