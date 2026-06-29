"""
Database Module
===============

MongoDB connection setup using pymongo.

This module provides a singleton-style database connection that is
initialized once and reused across the application. Uses connection
pooling internally (pymongo's default behavior).

Usage:
    from backend.database import get_db, init_db

    # Initialize on app startup
    init_db()

    # Get database reference anywhere
    db = get_db()
    db.users.find_one({"email": "user@example.com"})
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

import os
import sys

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Module-level references (singleton pattern)
_client: MongoClient = None
_db = None


def init_db():
    """
    Initialize the MongoDB connection.

    Call this once during application startup. Creates a MongoClient
    with connection pooling and verifies connectivity with a ping.

    Raises:
        SystemExit: If the database connection fails.
    """
    global _client, _db

    if _client is not None:
        logger.info("Database already initialized, skipping")
        return

    try:
        logger.info("Connecting to MongoDB...")

        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            maxPoolSize=50,
        )

        # Verify the connection works
        _client.admin.command("ping")

        # Extract database name from URI, default to "pdf_chatbot"
        db_name = settings.MONGODB_URI.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "pdf_chatbot"

        _db = _client[db_name]

        # Create indexes for efficient queries
        _ensure_indexes()

        logger.info(f"✅ Connected to MongoDB database: {db_name}")

    except ConnectionFailure as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        print(
            "\n❌ ERROR: Could not connect to MongoDB.\n"
            "\n"
            "Check your MONGODB_URI in .env:\n"
            f"  Current URI starts with: {settings.MONGODB_URI[:30]}...\n"
            "\n"
            "Common fixes:\n"
            "  1. Verify your MongoDB Atlas credentials\n"
            "  2. Whitelist your IP address in Atlas Network Access\n"
            "  3. Check if the cluster is running\n"
        )
        sys.exit(1)


def _ensure_indexes():
    """Create database indexes for performance."""
    # Unique email index on users
    _db.users.create_index("email", unique=True)

    # Index chat history by user_id and created_at for fast retrieval
    _db.chat_history.create_index([("user_id", 1), ("created_at", -1)])

    # Index pdf_documents by user_id
    _db.pdf_documents.create_index([("user_id", 1), ("uploaded_at", -1)])

    logger.info("Database indexes ensured")


def get_db():
    """
    Get the database reference.

    Returns the pymongo Database object. Must call init_db() first.

    Returns:
        pymongo.database.Database: The MongoDB database instance.

    Raises:
        RuntimeError: If init_db() hasn't been called yet.
    """
    if _db is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    return _db


def close_db():
    """Close the MongoDB connection (for graceful shutdown)."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")
