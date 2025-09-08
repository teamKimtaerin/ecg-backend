-- ECG Database Initial Setup
-- This script runs automatically when PostgreSQL container starts

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Users table matching SQLAlchemy model
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    auth_provider VARCHAR(50) DEFAULT 'local',
    oauth_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions (optional, depends on your setup)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kimtaerin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kimtaerin;