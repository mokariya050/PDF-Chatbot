"""
Data Models Module
==================

MongoDB data access layer for users, PDFs, and chat history.

Each "Model" class provides static methods for CRUD operations
on its corresponding MongoDB collection. No ORM is needed —
pymongo works directly with dictionaries.

Usage:
    from backend.models import UserModel, PDFModel, ChatModel

    # Create a user
    user_id = UserModel.create("Prashant", "prashant@email.com", "password123")

    # Save a PDF record
    pdf_id = PDFModel.create(user_id, "report.pdf", "Annual_Report.pdf", 42, 156, 3.2)

    # Save a chat message
    ChatModel.create(user_id, pdf_id, "What is the revenue?", "The revenue is...")
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict

import bcrypt
from bson import ObjectId

from backend.database import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


class UserModel:
    """CRUD operations for the 'users' collection."""

    COLLECTION = "users"

    @staticmethod
    def create(name: str, email: str, password: str) -> str:
        """
        Create a new user with a hashed password.

        Args:
            name: User's display name.
            email: User's email (must be unique).
            password: Plain-text password (will be hashed).

        Returns:
            str: The inserted user's ID as a string.

        Raises:
            pymongo.errors.DuplicateKeyError: If email already exists.
        """
        db = get_db()

        # Hash the password with bcrypt
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")

        user_doc = {
            "name": name,
            "email": email.lower().strip(),
            "password": password_hash,
            "created_at": datetime.now(timezone.utc),
        }

        result = db[UserModel.COLLECTION].insert_one(user_doc)
        logger.info(f"User created: {email}")
        return str(result.inserted_id)

    @staticmethod
    def find_by_email(email: str) -> Optional[Dict]:
        """Find a user by email address."""
        db = get_db()
        return db[UserModel.COLLECTION].find_one(
            {"email": email.lower().strip()}
        )

    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict]:
        """Find a user by their ObjectId."""
        db = get_db()
        try:
            return db[UserModel.COLLECTION].find_one(
                {"_id": ObjectId(user_id)}
            )
        except Exception:
            return None

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against a bcrypt hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


class PDFModel:
    """CRUD operations for the 'pdf_documents' collection."""

    COLLECTION = "pdf_documents"

    @staticmethod
    def create(
        user_id: str,
        filename: str,
        original_filename: str,
        num_pages: int,
        num_chunks: int,
        file_size_mb: float,
    ) -> str:
        """
        Record a newly uploaded PDF document.

        Args:
            user_id: The uploading user's ID.
            filename: Sanitized filename (from secure_filename).
            original_filename: Original filename from the user.
            num_pages: Number of pages extracted.
            num_chunks: Number of text chunks created.
            file_size_mb: File size in megabytes.

        Returns:
            str: The inserted document's ID as a string.
        """
        db = get_db()

        # Deactivate any previously active PDF for this user
        db[PDFModel.COLLECTION].update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}},
        )

        pdf_doc = {
            "user_id": user_id,
            "filename": filename,
            "original_filename": original_filename,
            "num_pages": num_pages,
            "num_chunks": num_chunks,
            "file_size_mb": round(file_size_mb, 2),
            "uploaded_at": datetime.now(timezone.utc),
            "is_active": True,
        }

        result = db[PDFModel.COLLECTION].insert_one(pdf_doc)
        logger.info(f"PDF record created: {filename} for user {user_id}")
        return str(result.inserted_id)

    @staticmethod
    def get_active_pdf(user_id: str) -> Optional[Dict]:
        """Get the currently active PDF for a user."""
        db = get_db()
        return db[PDFModel.COLLECTION].find_one(
            {"user_id": user_id, "is_active": True}
        )

    @staticmethod
    def get_user_pdfs(user_id: str, limit: int = 20) -> List[Dict]:
        """Get all PDFs uploaded by a user (most recent first)."""
        db = get_db()
        cursor = (
            db[PDFModel.COLLECTION]
            .find({"user_id": user_id})
            .sort("uploaded_at", -1)
            .limit(limit)
        )
        return list(cursor)

    @staticmethod
    def deactivate_all(user_id: str):
        """Deactivate all PDFs for a user (used on reset)."""
        db = get_db()
        db[PDFModel.COLLECTION].update_many(
            {"user_id": user_id},
            {"$set": {"is_active": False}},
        )
        logger.info(f"All PDFs deactivated for user {user_id}")


class ChatModel:
    """CRUD operations for the 'chat_history' collection."""

    COLLECTION = "chat_history"

    @staticmethod
    def create(
        user_id: str,
        pdf_id: str,
        question: str,
        answer: str,
    ) -> str:
        """
        Save a Q&A pair to chat history.

        Args:
            user_id: The user who asked.
            pdf_id: The PDF being queried.
            question: The user's question.
            answer: The AI-generated answer.

        Returns:
            str: The inserted chat record's ID.
        """
        db = get_db()

        chat_doc = {
            "user_id": user_id,
            "pdf_id": pdf_id,
            "question": question,
            "answer": answer,
            "created_at": datetime.now(timezone.utc),
        }

        result = db[ChatModel.COLLECTION].insert_one(chat_doc)
        logger.info(f"Chat saved for user {user_id}")
        return str(result.inserted_id)

    @staticmethod
    def get_user_history(
        user_id: str,
        limit: int = 50,
        pdf_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get chat history for a user, optionally filtered by PDF.

        Returns most recent conversations first.
        """
        db = get_db()
        query = {"user_id": user_id}
        if pdf_id:
            query["pdf_id"] = pdf_id

        cursor = (
            db[ChatModel.COLLECTION]
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        return list(cursor)

    @staticmethod
    def delete_by_user(user_id: str):
        """Delete all chat history for a user."""
        db = get_db()
        result = db[ChatModel.COLLECTION].delete_many({"user_id": user_id})
        logger.info(
            f"Deleted {result.deleted_count} chat records for user {user_id}"
        )
