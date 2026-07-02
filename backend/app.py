"""
Flask Backend Application
=========================

REST API server for the AI PDF Chatbot.

Endpoints:
    Auth:
        POST   /api/auth/signup  — Register a new user
        POST   /api/auth/login   — Login and get JWT token
        GET    /api/auth/me      — Get current user profile

    App (all require JWT):
        POST   /api/upload   — Upload a PDF file, process and embed it
        POST   /api/chat     — Ask a question about the uploaded PDF
        GET    /api/status   — Health check + PDF loaded status
        GET    /api/history  — Get chat history for current user
        DELETE /api/reset    — Clear uploaded PDF and vector store

Usage:
    python backend/app.py
"""

import os
import sys
import shutil

# Add parent directory to path so we can import config and utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import settings
from backend.database import init_db, get_db
from backend.auth import auth_bp, jwt_required, get_current_user_id
from backend.models import PDFModel, ChatModel
from utils.logger import get_logger
from utils.pdf_loader import load_pdf
from utils.text_chunker import chunk_documents
from utils.embedder import create_vector_store, load_vector_store
from utils.rag_chain import get_answer

logger = get_logger(__name__)

# ----------------------------------------------------------------
# Flask App Setup
# ----------------------------------------------------------------
app = Flask(__name__)

# Configure CORS — allow frontend origin in production and localhost in dev
allowed_origins = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",   # Alternative dev port
]
if settings.FRONTEND_URL:
    allowed_origins.append(settings.FRONTEND_URL)

CORS(app, origins=allowed_origins, supports_credentials=True)

# Register authentication blueprint
app.register_blueprint(auth_bp)

# In-memory cache for vector stores (keyed by user_id)
# The vector store is an in-memory FAISS index, not suitable for PostgreSQL.
# We cache it here and persist to disk via FAISS save/load.
_vector_stores = {}


# ----------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------
def _allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in settings.ALLOWED_EXTENSIONS


def _file_size_ok(file) -> bool:
    """Check if file size is within the limit."""
    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    return size_mb <= settings.MAX_FILE_SIZE_MB


def _get_file_size_mb(file) -> float:
    """Get file size in MB without consuming the stream."""
    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    return size_mb


def _get_user_vectorstore_dir(user_id: str) -> str:
    """Get the vector store directory path for a specific user."""
    user_dir = settings.VECTORSTORE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return str(user_dir)


# ----------------------------------------------------------------
# Health Check (for Render)
# ----------------------------------------------------------------
@app.route("/", methods=["GET"])
def health_check():
    """Root health check endpoint for Render deployment."""
    return jsonify({
        "status": "healthy",
        "service": "PDF ChatBot API",
        "version": "1.0.0",
    })


# ----------------------------------------------------------------
# Routes
# ----------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
@jwt_required
def status():
    """Health check and current PDF status for authenticated user."""
    user_id = get_current_user_id()
    active_pdf = PDFModel.get_active_pdf(user_id)

    return jsonify({
        "status": "ok",
        "pdf_loaded": active_pdf is not None,
        "pdf_name": active_pdf["filename"] if active_pdf else None,
        "num_pages": active_pdf["num_pages"] if active_pdf else 0,
        "num_chunks": active_pdf["num_chunks"] if active_pdf else 0,
    })


@app.route("/api/upload", methods=["POST"])
@jwt_required
def upload_pdf():
    """
    Upload and process a PDF file.

    Process:
        1. Validate the file (extension, size).
        2. Save to uploads directory.
        3. Extract text with PyPDFLoader.
        4. Chunk the text.
        5. Create embeddings and FAISS vector store.
        6. Save PDF metadata to PostgreSQL.

    Returns:
        JSON with processing results or error message.
    """
    user_id = get_current_user_id()

    # Check if file is in the request
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file extension
    if not _allowed_file(file.filename):
        return jsonify({
            "error": f"Invalid file type. Only PDF files are allowed."
        }), 400

    # Validate file size
    if not _file_size_ok(file):
        return jsonify({
            "error": f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB."
        }), 400

    try:
        # Get file size before saving
        file_size_mb = _get_file_size_mb(file)

        # Save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(str(settings.UPLOAD_DIR), filename)
        file.save(filepath)
        logger.info(f"File saved: {filepath}")

        # Step 1: Load PDF
        documents = load_pdf(filepath)

        # Step 2: Chunk text
        chunks = chunk_documents(documents)

        # Step 3: Create vector store (user-specific directory)
        vector_store_dir = _get_user_vectorstore_dir(user_id)
        vector_store = create_vector_store(chunks)

        # Save vector store to user-specific directory
        vector_store.save_local(vector_store_dir)

        # Cache vector store in memory
        _vector_stores[user_id] = vector_store

        # Step 4: Save PDF metadata to PostgreSQL
        pdf_id = PDFModel.create(
            user_id=user_id,
            filename=filename,
            original_filename=file.filename,
            num_pages=len(documents),
            num_chunks=len(chunks),
            file_size_mb=file_size_mb,
        )

        logger.info(
            f"PDF processed successfully: {filename} "
            f"({len(documents)} pages, {len(chunks)} chunks) "
            f"for user {user_id}"
        )

        return jsonify({
            "message": "PDF uploaded and processed successfully!",
            "filename": filename,
            "num_pages": len(documents),
            "num_chunks": len(chunks),
            "pdf_id": pdf_id,
        })

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
@jwt_required
def chat():
    """
    Ask a question about the uploaded PDF.

    Expects JSON body: { "question": "your question here" }

    Returns:
        JSON with the generated answer.
    """
    user_id = get_current_user_id()

    # Get or load vector store for this user
    vector_store = _vector_stores.get(user_id)

    if vector_store is None:
        # Try loading from disk
        vector_store_dir = _get_user_vectorstore_dir(user_id)
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS

        index_file = os.path.join(vector_store_dir, "index.faiss")
        if os.path.exists(index_file):
            embedding_model = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            vector_store = FAISS.load_local(
                vector_store_dir,
                embedding_model,
                allow_dangerous_deserialization=True,
            )
            _vector_stores[user_id] = vector_store
        else:
            return jsonify({
                "error": "No PDF uploaded yet. Please upload a PDF first."
            }), 400

    # Get question from request body
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    try:
        answer = get_answer(vector_store, question)

        # Save to chat history in PostgreSQL
        active_pdf = PDFModel.get_active_pdf(user_id)
        pdf_id = str(active_pdf["id"]) if active_pdf else None

        ChatModel.create(
            user_id=user_id,
            pdf_id=pdf_id,
            question=question,
            answer=answer,
        )

        return jsonify({
            "answer": answer,
            "question": question,
            "pdf_name": active_pdf["filename"] if active_pdf else None,
        })

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500


@app.route("/api/history", methods=["GET"])
@jwt_required
def get_history():
    """
    Get chat history for the current user.

    Query params:
        pdf_id (optional): Filter by specific PDF document.
        limit (optional): Max number of results (default 50).

    Returns:
        JSON with list of chat Q&A pairs.
    """
    user_id = get_current_user_id()
    pdf_id = request.args.get("pdf_id")
    limit = int(request.args.get("limit", "50"))

    history = ChatModel.get_user_history(user_id, limit=limit, pdf_id=pdf_id)

    # Format for JSON response
    result = []
    for chat in history:
        result.append({
            "id": str(chat["id"]),
            "question": chat["question"],
            "answer": chat["answer"],
            "pdf_id": str(chat["pdf_id"]) if chat.get("pdf_id") else None,
            "created_at": chat["created_at"].isoformat(),
        })

    return jsonify({"history": result})


@app.route("/api/reset", methods=["DELETE"])
@jwt_required
def reset():
    """
    Clear the uploaded PDF and vector store for the current user.

    Removes uploaded files and FAISS index from disk,
    resets the in-memory state, and deactivates PDFs in PostgreSQL.
    """
    user_id = get_current_user_id()

    try:
        # Clear uploads directory
        for f in settings.UPLOAD_DIR.iterdir():
            if f.name != ".gitkeep":
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)

        # Clear user's vector store directory
        user_vs_dir = settings.VECTORSTORE_DIR / user_id
        if user_vs_dir.exists():
            shutil.rmtree(user_vs_dir)

        # Remove from memory cache
        _vector_stores.pop(user_id, None)

        # Deactivate PDFs in PostgreSQL
        PDFModel.deactivate_all(user_id)

        logger.info(f"Application state reset for user {user_id}")
        return jsonify({"message": "Reset successful. Upload a new PDF to start."})

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return jsonify({"error": f"Reset failed: {str(e)}"}), 500


# ----------------------------------------------------------------
# Startup
# ----------------------------------------------------------------
# Initialize PostgreSQL on import so gunicorn workers also connect
init_db()

if __name__ == "__main__":
    print("=" * 60)
    print("  AI PDF Chatbot - Flask Backend")
    print("=" * 60)
    print(f"  LLM Model:    {settings.LLM_MODEL_NAME}")
    print(f"  Embedding:    {settings.EMBEDDING_MODEL_NAME}")
    print(f"  Chunk Size:   {settings.CHUNK_SIZE}")
    print(f"  Top-K:        {settings.TOP_K}")
    print(f"  Upload Dir:   {settings.UPLOAD_DIR}")
    print(f"  Database:     PostgreSQL (Supabase) ✅")
    print("=" * 60)

    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Starting server on http://localhost:{port}\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
