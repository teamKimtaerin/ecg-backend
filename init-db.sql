-- ECG Database Initial Setup
-- This script runs automatically when PostgreSQL container starts

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Example: Create a users table (you can modify this based on your needs)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example: Create a videos table
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    file_key VARCHAR(500) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example: Create a job_results table
CREATE TABLE IF NOT EXISTS job_results (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL,
    video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    result_data JSONB,
    status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_job_results_job_id ON job_results(job_id);
CREATE INDEX IF NOT EXISTS idx_job_results_status ON job_results(status);

-- Grant permissions (optional, depends on your setup)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ecg_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ecg_user;