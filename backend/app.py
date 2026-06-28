"""
Flask Backend Application
=========================

REST API server for the AI PDF Chatbot.

Endpoints:
    POST   /api/upload  — Upload a PDF file, process and embed it
    POST   /api/chat    — Ask a question about the uploaded PDF
    GET    /api/status  — Health check + PDF loaded status
    DELETE /api/reset   — Clear uploaded PDF and vector store

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
CORS(app)  # Allow cross-origin requests from Vite dev server

# In-memory state tracking
app_state = {
    "pdf_loaded": False,
    "pdf_name": None,
    "num_pages": 0,
    "num_chunks": 0,
    "vector_store": None,
}


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


# ----------------------------------------------------------------
# Routes
# ----------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def status():
    """Health check and current PDF status."""
    return jsonify({
        "status": "ok",
        "pdf_loaded": app_state["pdf_loaded"],
        "pdf_name": app_state["pdf_name"],
        "num_pages": app_state["num_pages"],
        "num_chunks": app_state["num_chunks"],
    })


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    """
    Upload and process a PDF file.

    Process:
        1. Validate the file (extension, size).
        2. Save to uploads directory.
        3. Extract text with PyPDFLoader.
        4. Chunk the text.
        5. Create embeddings and FAISS vector store.

    Returns:
        JSON with processing results or error message.
    """
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
        # Save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(str(settings.UPLOAD_DIR), filename)
        file.save(filepath)
        logger.info(f"File saved: {filepath}")

        # Step 1: Load PDF
        documents = load_pdf(filepath)

        # Step 2: Chunk text
        chunks = chunk_documents(documents)

        # Step 3: Create vector store
        vector_store = create_vector_store(chunks)

        # Update app state
        app_state["pdf_loaded"] = True
        app_state["pdf_name"] = filename
        app_state["num_pages"] = len(documents)
        app_state["num_chunks"] = len(chunks)
        app_state["vector_store"] = vector_store

        logger.info(
            f"PDF processed successfully: {filename} "
            f"({len(documents)} pages, {len(chunks)} chunks)"
        )

        return jsonify({
            "message": "PDF uploaded and processed successfully!",
            "filename": filename,
            "num_pages": len(documents),
            "num_chunks": len(chunks),
        })

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Ask a question about the uploaded PDF.

    Expects JSON body: { "question": "your question here" }

    Returns:
        JSON with the generated answer.
    """
    # Check if a PDF is loaded
    if not app_state["pdf_loaded"] or app_state["vector_store"] is None:
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
        answer = get_answer(app_state["vector_store"], question)

        return jsonify({
            "answer": answer,
            "question": question,
            "pdf_name": app_state["pdf_name"],
        })

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500


@app.route("/api/reset", methods=["DELETE"])
def reset():
    """
    Clear the uploaded PDF and vector store.

    Removes uploaded files and FAISS index from disk,
    resets the in-memory state.
    """
    try:
        # Clear uploads directory
        for f in settings.UPLOAD_DIR.iterdir():
            if f.name != ".gitkeep":
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)

        # Clear vector store directory
        for f in settings.VECTORSTORE_DIR.iterdir():
            if f.name != ".gitkeep":
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)

        # Reset state
        app_state["pdf_loaded"] = False
        app_state["pdf_name"] = None
        app_state["num_pages"] = 0
        app_state["num_chunks"] = 0
        app_state["vector_store"] = None

        logger.info("Application state reset successfully")
        return jsonify({"message": "Reset successful. Upload a new PDF to start."})

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return jsonify({"error": f"Reset failed: {str(e)}"}), 500


# ----------------------------------------------------------------
# Startup
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  AI PDF Chatbot - Flask Backend")
    print("=" * 60)
    print(f"  LLM Model:    {settings.LLM_MODEL_NAME}")
    print(f"  Embedding:    {settings.EMBEDDING_MODEL_NAME}")
    print(f"  Chunk Size:   {settings.CHUNK_SIZE}")
    print(f"  Top-K:        {settings.TOP_K}")
    print(f"  Upload Dir:   {settings.UPLOAD_DIR}")
    print("=" * 60)

    # Try to load existing vector store on startup
    existing_store = load_vector_store()
    if existing_store:
        app_state["vector_store"] = existing_store
        app_state["pdf_loaded"] = True
        app_state["pdf_name"] = "(previously loaded)"
        print("  [OK] Loaded existing vector store from disk")

    print("\n  Starting server on http://localhost:5000\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
