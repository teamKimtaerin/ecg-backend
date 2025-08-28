# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the backend for an Expressive Caption Generator application built with FastAPI. The project is currently in early development stage with the basic structure set up but implementation pending.

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
  - **core/**: Core configurations and settings
    - **config.py**: Environment variables and application settings
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
- **Pydantic Settings**: Configuration management

### API Documentation
When the server is running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Important Notes

- The project follows a typical FastAPI application structure with separation of concerns between API endpoints, business logic (services), and data models
- Environment variables should be configured in `.env` file (use `.env.example` as template)
- The application is set up for versioned APIs (v1) to allow for backward compatibility as the API evolves