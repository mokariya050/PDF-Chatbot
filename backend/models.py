"""
Data Models Module
==================

PostgreSQL data access layer for users, PDFs, and chat history.

Each "Model" class provides static methods for CRUD operations
on its corresponding PostgreSQL table. Uses parameterized queries
to prevent SQL injection.

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

from backend.database import get_db, release_db
from utils.logger import get_logger

logger = get_logger(__name__)


class UserModel:
    """CRUD operations for the 'users' table."""

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
            psycopg2.errors.UniqueViolation: If email already exists.
        """
        conn = get_db()

        # Hash the password with bcrypt
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (name, email, password)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email.lower().strip(), password_hash),
                )
                user_id = cur.fetchone()[0]
                conn.commit()

            logger.info(f"User created: {email}")
            return str(user_id)

        except Exception:
            conn.rollback()
            raise
        finally:
            release_db(conn)

    @staticmethod
    def find_by_email(email: str) -> Optional[Dict]:
        """Find a user by email address."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, email, password, created_at FROM users WHERE email = %s",
                    (email.lower().strip(),),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "email": row[2],
                        "password": row[3],
                        "created_at": row[4],
                    }
                return None
        finally:
            release_db(conn)

    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict]:
        """Find a user by their ID."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, email, password, created_at FROM users WHERE id = %s",
                    (int(user_id),),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "email": row[2],
                        "password": row[3],
                        "created_at": row[4],
                    }
                return None
        except (ValueError, TypeError):
            return None
        finally:
            release_db(conn)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against a bcrypt hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


class PDFModel:
    """CRUD operations for the 'pdf_documents' table."""

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
        conn = get_db()

        try:
            with conn.cursor() as cur:
                # Deactivate any previously active PDF for this user
                cur.execute(
                    "UPDATE pdf_documents SET is_active = FALSE WHERE user_id = %s AND is_active = TRUE",
                    (int(user_id),),
                )

                # Insert the new PDF record
                cur.execute(
                    """
                    INSERT INTO pdf_documents (user_id, filename, original_filename, num_pages, num_chunks, file_size_mb)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (int(user_id), filename, original_filename, num_pages, num_chunks, round(file_size_mb, 2)),
                )
                pdf_id = cur.fetchone()[0]
                conn.commit()

            logger.info(f"PDF record created: {filename} for user {user_id}")
            return str(pdf_id)

        except Exception:
            conn.rollback()
            raise
        finally:
            release_db(conn)

    @staticmethod
    def get_active_pdf(user_id: str) -> Optional[Dict]:
        """Get the currently active PDF for a user."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, filename, original_filename, num_pages, num_chunks, file_size_mb, uploaded_at, is_active
                    FROM pdf_documents
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY uploaded_at DESC
                    LIMIT 1
                    """,
                    (int(user_id),),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "filename": row[2],
                        "original_filename": row[3],
                        "num_pages": row[4],
                        "num_chunks": row[5],
                        "file_size_mb": row[6],
                        "uploaded_at": row[7],
                        "is_active": row[8],
                    }
                return None
        finally:
            release_db(conn)

    @staticmethod
    def get_user_pdfs(user_id: str, limit: int = 20) -> List[Dict]:
        """Get all PDFs uploaded by a user (most recent first)."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, filename, original_filename, num_pages, num_chunks, file_size_mb, uploaded_at, is_active
                    FROM pdf_documents
                    WHERE user_id = %s
                    ORDER BY uploaded_at DESC
                    LIMIT %s
                    """,
                    (int(user_id), limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "filename": row[2],
                        "original_filename": row[3],
                        "num_pages": row[4],
                        "num_chunks": row[5],
                        "file_size_mb": row[6],
                        "uploaded_at": row[7],
                        "is_active": row[8],
                    }
                    for row in rows
                ]
        finally:
            release_db(conn)

    @staticmethod
    def deactivate_all(user_id: str):
        """Deactivate all PDFs for a user (used on reset)."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE pdf_documents SET is_active = FALSE WHERE user_id = %s",
                    (int(user_id),),
                )
                conn.commit()
            logger.info(f"All PDFs deactivated for user {user_id}")
        except Exception:
            conn.rollback()
            raise
        finally:
            release_db(conn)


class ChatModel:
    """CRUD operations for the 'chat_history' table."""

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
        conn = get_db()

        try:
            # Handle "unknown" pdf_id gracefully
            pdf_id_int = None
            try:
                pdf_id_int = int(pdf_id)
            except (ValueError, TypeError):
                pdf_id_int = None

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_history (user_id, pdf_id, question, answer)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (int(user_id), pdf_id_int, question, answer),
                )
                chat_id = cur.fetchone()[0]
                conn.commit()

            logger.info(f"Chat saved for user {user_id}")
            return str(chat_id)

        except Exception:
            conn.rollback()
            raise
        finally:
            release_db(conn)

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
        conn = get_db()
        try:
            with conn.cursor() as cur:
                if pdf_id:
                    cur.execute(
                        """
                        SELECT id, user_id, pdf_id, question, answer, created_at
                        FROM chat_history
                        WHERE user_id = %s AND pdf_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (int(user_id), int(pdf_id), limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_id, pdf_id, question, answer, created_at
                        FROM chat_history
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (int(user_id), limit),
                    )

                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "pdf_id": row[2],
                        "question": row[3],
                        "answer": row[4],
                        "created_at": row[5],
                    }
                    for row in rows
                ]
        finally:
            release_db(conn)

    @staticmethod
    def delete_by_user(user_id: str):
        """Delete all chat history for a user."""
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_history WHERE user_id = %s",
                    (int(user_id),),
                )
                deleted = cur.rowcount
                conn.commit()
            logger.info(
                f"Deleted {deleted} chat records for user {user_id}"
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            release_db(conn)
