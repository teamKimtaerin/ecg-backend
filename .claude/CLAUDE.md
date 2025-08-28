# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the backend for an Expressive Caption Generator application built with FastAPI. The project integrates AWS and OpenAI services for caption generation functionality.

## Commands

### Development Server
```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Start on specific port (default is 8000)
uvicorn app.main:app --reload --port 8080
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

### Directory Structure
- **app/**: Main application code
  - **main.py**: FastAPI application entry point
  - **core/config.py**: AWS, OpenAI and other environment configurations
  - **api/v1/**: Versioned API endpoints
    - **endpoints/**: Individual endpoint implementations
    - **routers.py**: Router registration and setup
  - **models/**: SQLAlchemy database models
  - **schemas/**: Pydantic models for request/response validation
  - **services/**: Business logic layer
  - **db/**: Database connection and session management

### Key Technologies
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **SQLAlchemy**: ORM for database models
- **Pydantic**: Data validation using Python type annotations
- **AWS Services**: Cloud infrastructure integration
- **OpenAI API**: AI-powered caption generation

### API Documentation
When the server is running, API documentation is available at:
- Swagger UI (interactive): http://localhost:8000/docs
- ReDoc (read-only): http://localhost:8000/redoc

## Important Configuration

Environment variables are managed through `.env` file. Key configurations include:
- AWS credentials and settings
- OpenAI API configuration
- Application secrets and debug settings

The project follows a typical FastAPI application structure with clear separation between API layer, business logic (services), and data models.