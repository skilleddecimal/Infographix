"""Database base configuration."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./infographix.db"  # Default to SQLite for development
)

# Handle special cases for different databases
if DATABASE_URL.startswith("postgres://"):
    # Fix for SQLAlchemy 1.4+ (postgresql:// required)
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Get database session.

    Yields:
        Database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)
