"""
Embedder Module
===============

Handles text embedding and FAISS vector store operations.

This module:
    1. Converts text chunks into numerical vectors (embeddings)
       using a HuggingFace sentence-transformer model.
    2. Stores embeddings in a FAISS index for fast similarity search.
    3. Provides retrieval interface for the RAG chain.

The embedding model runs LOCALLY — no API key needed.
Only the LLM (Gemini) requires an API key.

Usage:
    from utils.embedder import create_vector_store, load_vector_store

    # Create new vector store from chunks
    vector_store = create_vector_store(chunks)

    # Load existing vector store
    vector_store = load_vector_store()

    # Search for similar chunks
    results = vector_store.similarity_search("What is AI?", k=4)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Module-level cache for the embedding model.
# Loading the model takes ~2-5 seconds, so we cache it after first use.
_embedding_model: Optional[HuggingFaceEmbeddings] = None


def _get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Get or create the HuggingFace embedding model (cached singleton).

    The model is downloaded on first use (~90 MB) and cached locally
    by HuggingFace's transformers library.

    Returns:
        HuggingFaceEmbeddings: Configured embedding model instance.
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding model loaded successfully")

    return _embedding_model


def create_vector_store(chunks: List[Document]) -> FAISS:
    """
    Create a FAISS vector store from document chunks.

    Process:
        1. Each chunk's text is converted to a 384-dimensional vector
           by the embedding model.
        2. All vectors are indexed in a FAISS flat index for exact
           nearest-neighbor search.
        3. The index is saved to disk for persistence.

    Args:
        chunks: List of Document objects (text chunks) to embed.

    Returns:
        FAISS: Vector store instance ready for similarity search.

    Raises:
        ValueError: If chunks list is empty.
    """
    if not chunks:
        logger.error("No chunks provided for vector store creation")
        raise ValueError("Cannot create vector store from empty chunks")

    logger.info(f"Creating vector store from {len(chunks)} chunks...")

    embedding_model = _get_embedding_model()
    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding_model,
    )

    # Save to disk for persistence
    save_path = str(settings.VECTORSTORE_DIR)
    vector_store.save_local(save_path)
    logger.info(f"Vector store saved to: {save_path}")

    return vector_store


def load_vector_store() -> Optional[FAISS]:
    """
    Load a previously saved FAISS vector store from disk.

    Returns:
        FAISS: Loaded vector store, or None if no store exists.
    """
    save_path = str(settings.VECTORSTORE_DIR)
    index_file = settings.VECTORSTORE_DIR / "index.faiss"

    if not index_file.exists():
        logger.warning("No vector store found on disk")
        return None

    logger.info("Loading vector store from disk...")
    embedding_model = _get_embedding_model()

    try:
        vector_store = FAISS.load_local(
            save_path,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
        logger.info("Vector store loaded successfully")
        return vector_store
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        return None
