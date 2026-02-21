-- Infographix PostgreSQL Initialization Script
-- This script runs on first container startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create application schema
CREATE SCHEMA IF NOT EXISTS infographix;

-- Set search path
SET search_path TO infographix, public;

-- Grant permissions
GRANT ALL ON SCHEMA infographix TO infographix;
GRANT ALL ON ALL TABLES IN SCHEMA infographix TO infographix;
GRANT ALL ON ALL SEQUENCES IN SCHEMA infographix TO infographix;

-- Create indexes for common queries (handled by SQLAlchemy migrations normally)
-- These are placeholders - actual indexes created via Alembic migrations

-- Performance settings for development
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET effective_cache_size = '512MB';

-- Logging settings for development
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = 'on';
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries > 100ms

-- Output confirmation
DO $$
BEGIN
    RAISE NOTICE 'Infographix database initialized successfully';
END $$;
