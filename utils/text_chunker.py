"""
Text Chunker Module
===================

Splits large documents into smaller, overlapping text chunks
for embedding and retrieval.

Why chunking?
    LLMs have context limits, and embedding models work best with
    focused, topic-coherent text. By splitting documents into
    ~1000-character chunks with overlap, we:
    1. Enable precise retrieval (find the exact relevant section).
    2. Prevent context loss at chunk boundaries (overlap helps).
    3. Stay within embedding model input limits.

Usage:
    from utils.text_chunker import chunk_documents

    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split a list of documents into smaller, overlapping chunks.

    Uses RecursiveCharacterTextSplitter which tries to split on
    natural boundaries (paragraphs → sentences → words) to keep
    chunks semantically coherent.

    Args:
        documents: List of Document objects from the PDF loader.

    Returns:
        List of smaller Document objects (chunks), each containing:
            - page_content: The chunk text.
            - metadata: Original metadata plus chunk index info.

    Raises:
        ValueError: If documents list is empty.
    """
    if not documents:
        logger.error("No documents provided for chunking")
        raise ValueError("Cannot chunk an empty document list")

    logger.info(
        f"Chunking {len(documents)} documents "
        f"(chunk_size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP})"
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(documents)

    logger.info(
        f"Created {len(chunks)} chunks from {len(documents)} pages "
        f"(avg {sum(len(c.page_content) for c in chunks) // max(len(chunks), 1)} chars/chunk)"
    )

    return chunks
