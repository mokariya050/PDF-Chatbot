"""
PDF Loader Module
=================

Handles loading and extracting text from uploaded PDF files.

Uses LangChain's PyPDFLoader to parse PDF documents into
a list of Document objects, one per page.

Usage:
    from utils.pdf_loader import load_pdf

    documents = load_pdf("/path/to/file.pdf")
    for doc in documents:
        print(doc.page_content[:100])
"""

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from utils.logger import get_logger

logger = get_logger(__name__)


def load_pdf(file_path: str) -> List[Document]:
    """
    Load a PDF file and extract text content from each page.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        List of Document objects, one per page, containing:
            - page_content: The extracted text from that page.
            - metadata: Dict with 'source' (file path) and 'page' (page number).

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the file is not a PDF.
        Exception: If PyPDFLoader fails to parse the file.
    """
    path = Path(file_path)

    if not path.exists():
        logger.error(f"PDF file not found: {file_path}")
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        logger.error(f"Invalid file type: {path.suffix}")
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    logger.info(f"Loading PDF: {path.name}")

    try:
        loader = PyPDFLoader(str(path))
        documents = loader.load()

        total_chars = sum(len(doc.page_content) for doc in documents)
        logger.info(
            f"PDF loaded successfully: {len(documents)} pages, "
            f"{total_chars:,} characters total"
        )

        # Filter out empty pages
        non_empty = [doc for doc in documents if doc.page_content.strip()]
        if len(non_empty) < len(documents):
            logger.warning(
                f"Filtered out {len(documents) - len(non_empty)} empty pages"
            )

        return non_empty

    except Exception as e:
        logger.error(f"Failed to load PDF '{path.name}': {e}")
        raise
