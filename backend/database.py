"""
Database Module
===============

PostgreSQL (Supabase) connection setup using psycopg2.

This module provides a connection pool that is initialized once
and reused across the application. Uses psycopg2's built-in
connection pooling for efficient database access.

Usage:
    from backend.database import get_db, init_db

    # Initialize on app startup
    init_db()

    # Get database connection anywhere
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
"""

import os
import sys

import psycopg2
from psycopg2 import pool, extras

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Module-level connection pool (singleton pattern)
_pool: pool.SimpleConnectionPool = None


def init_db():
    """
    Initialize the PostgreSQL connection pool and create tables.

    Call this once during application startup. Creates a connection
    pool with min 1 and max 20 connections, then ensures all required
    tables exist.

    Raises:
        SystemExit: If the database connection fails.
    """
    global _pool

    if _pool is not None:
        logger.info("Database already initialized, skipping")
        return

    try:
        logger.info("Connecting to PostgreSQL (Supabase)...")

        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=settings.DATABASE_URL,
        )

        # Verify the connection works
        conn = _pool.getconn()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        _pool.putconn(conn)

        # Create tables if they don't exist
        _create_tables()

        logger.info("✅ Connected to PostgreSQL (Supabase)")

    except psycopg2.OperationalError as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        print(
            "\n❌ ERROR: Could not connect to PostgreSQL (Supabase).\n"
            "\n"
            "Check your DATABASE_URL in .env:\n"
            f"  Current URI starts with: {settings.DATABASE_URL[:40]}...\n"
            "\n"
            "Common fixes:\n"
            "  1. Verify your Supabase database password\n"
            "  2. Check if the Supabase project is running\n"
            "  3. Ensure the connection string is correct\n"
            "     Format: postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres\n"
        )
        sys.exit(1)


def _create_tables():
    """Create database tables if they don't exist."""
    conn = get_db()
    conn.autocommit = True

    with conn.cursor() as cur:
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                email       VARCHAR(255) UNIQUE NOT NULL,
                password    VARCHAR(255) NOT NULL,
                created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        # PDF documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pdf_documents (
                id                  SERIAL PRIMARY KEY,
                user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename            VARCHAR(255) NOT NULL,
                original_filename   VARCHAR(255) NOT NULL,
                num_pages           INTEGER NOT NULL DEFAULT 0,
                num_chunks          INTEGER NOT NULL DEFAULT 0,
                file_size_mb        REAL NOT NULL DEFAULT 0,
                uploaded_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_active           BOOLEAN DEFAULT TRUE
            )
        """)

        # Chat history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                pdf_id      INTEGER REFERENCES pdf_documents(id) ON DELETE SET NULL,
                question    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdf_documents_user_id
            ON pdf_documents(user_id, uploaded_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_user_id
            ON chat_history(user_id, created_at DESC)
        """)

    release_db(conn)
    logger.info("Database tables and indexes ensured")


def get_db():
    """
    Get a database connection from the pool.

    Returns a psycopg2 connection object. The caller MUST call
    release_db(conn) when done to return it to the pool.

    Returns:
        psycopg2.connection: A PostgreSQL connection.

    Raises:
        RuntimeError: If init_db() hasn't been called yet.
    """
    if _pool is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    return _pool.getconn()


def release_db(conn):
    """Return a connection back to the pool."""
    if _pool is not None and conn is not None:
        _pool.putconn(conn)


def close_db():
    """Close all connections in the pool (for graceful shutdown)."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")
