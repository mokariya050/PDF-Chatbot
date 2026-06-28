"""
Central Configuration Module
=============================

This module is the SINGLE SOURCE OF TRUTH for all application settings.
Every other module imports configuration from here — no hardcoded values
anywhere else in the codebase.

How it works:
    1. Loads environment variables from .env file using python-dotenv.
    2. Reads each variable with sensible defaults for optional settings.
    3. Validates that required variables (like API keys) are present.
    4. Exposes a frozen (immutable) Settings dataclass instance.

Usage:
    from config import settings
    print(settings.GOOGLE_API_KEY)
    print(settings.CHUNK_SIZE)
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


# ----------------------------------------------------------------
# Step 1: Define project paths (needed for .env loading)
# ----------------------------------------------------------------
# Path(__file__).parent resolves to the directory containing config.py,
# which is the project root. Using Path objects instead of string
# concatenation is a Python best practice — it handles OS-specific
# path separators (/ vs \) automatically.
BASE_DIR = Path(__file__).parent


# ----------------------------------------------------------------
# Step 2: Load .env file into os.environ
# ----------------------------------------------------------------
# We explicitly point to the .env file in the project root so that
# it works regardless of which directory the server is started from
# (e.g., running from backend/ or the project root).
#
# override=False means: if a variable is already set in the real
# environment (e.g., via Docker or CI/CD), the .env file won't
# overwrite it. This is important for production deployments.
_dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=_dotenv_path, override=False)


# ----------------------------------------------------------------
# Step 3: Define remaining project paths
# ----------------------------------------------------------------
UPLOAD_DIR = BASE_DIR / "uploads"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
LOG_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"


# ----------------------------------------------------------------
# Step 3: Settings dataclass
# ----------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from environment variables.

    Frozen=True makes this dataclass IMMUTABLE after creation.
    This prevents accidental modification of settings at runtime,
    which could cause hard-to-debug issues.

    Attributes:
        GOOGLE_API_KEY: API key for Google Gemini (required).
        LLM_MODEL_NAME: Gemini model identifier.
        LLM_TEMPERATURE: Controls randomness in LLM responses.
            - 0.0 = deterministic (same input → same output)
            - 1.0 = creative (more varied responses)
            - For factual Q&A, keep low (0.1-0.3).
        EMBEDDING_MODEL_NAME: HuggingFace model for text embeddings.
        CHUNK_SIZE: Number of characters per text chunk.
            - Larger chunks = more context but less precise retrieval.
            - Smaller chunks = more precise but may lose context.
            - 1000 is a good default for most documents.
        CHUNK_OVERLAP: Characters of overlap between consecutive chunks.
            - Prevents losing context at chunk boundaries.
            - Typically 10-20% of CHUNK_SIZE.
        TOP_K: Number of most relevant chunks to retrieve per query.
            - Higher = more context for LLM but more noise.
            - 3-5 is ideal for most use cases.
        MAX_FILE_SIZE_MB: Maximum allowed upload file size in MB.
        ALLOWED_EXTENSIONS: Set of allowed file extensions for upload.
    """

    # --- Required Settings (no defaults) ---
    GOOGLE_API_KEY: str

    # --- LLM Settings ---
    LLM_MODEL_NAME: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.2

    # --- Embedding Settings ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Chunking Settings ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # --- Retrieval Settings ---
    TOP_K: int = 4

    # --- Upload Settings ---
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: frozenset = field(
        default_factory=lambda: frozenset({".pdf"})
    )

    # --- Directory Paths ---
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    VECTORSTORE_DIR: Path = VECTORSTORE_DIR
    LOG_DIR: Path = LOG_DIR
    ASSETS_DIR: Path = ASSETS_DIR


def _load_settings() -> Settings:
    """
    Load and validate application settings from environment variables.

    This function:
        1. Reads each environment variable with os.getenv().
        2. Converts types (str → int, str → float) where needed.
        3. Validates that required variables are present.
        4. Returns an immutable Settings instance.

    Returns:
        Settings: Validated, frozen configuration object.

    Raises:
        SystemExit: If required environment variables are missing.
            We use sys.exit() instead of raising an exception because
            a missing API key is a FATAL configuration error — the
            app cannot function without it.
    """
    # --- Read required variables ---
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key or google_api_key == "your_google_api_key_here":
        print(
            "\n❌ ERROR: GOOGLE_API_KEY is not set or still has the placeholder value.\n"
            "\n"
            "To fix this:\n"
            "  1. Copy .env.example to .env:  cp .env.example .env\n"
            "  2. Open .env and paste your real Google API key.\n"
            "  3. Get a free key at: https://aistudio.google.com/apikey\n"
        )
        sys.exit(1)

    # --- Read optional variables with type conversion ---
    # os.getenv() always returns strings, so we convert to the right type.
    # The pattern: type(os.getenv("KEY", "default_as_string"))
    llm_model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    embedding_model_name = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    top_k = int(os.getenv("TOP_K", "4"))
    max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

    # --- Validate logical constraints ---
    if chunk_overlap >= chunk_size:
        print(
            f"\n⚠️  WARNING: CHUNK_OVERLAP ({chunk_overlap}) must be less than "
            f"CHUNK_SIZE ({chunk_size}). Using default values.\n"
        )
        chunk_size = 1000
        chunk_overlap = 200

    if top_k < 1:
        print("\n⚠️  WARNING: TOP_K must be at least 1. Using default (4).\n")
        top_k = 4

    if llm_temperature < 0.0 or llm_temperature > 1.0:
        print(
            "\n⚠️  WARNING: LLM_TEMPERATURE must be between 0.0 and 1.0. "
            "Using default (0.2).\n"
        )
        llm_temperature = 0.2

    # --- Ensure directories exist ---
    # exist_ok=True means: don't raise an error if the directory already exists.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    return Settings(
        GOOGLE_API_KEY=google_api_key,
        LLM_MODEL_NAME=llm_model_name,
        LLM_TEMPERATURE=llm_temperature,
        EMBEDDING_MODEL_NAME=embedding_model_name,
        CHUNK_SIZE=chunk_size,
        CHUNK_OVERLAP=chunk_overlap,
        TOP_K=top_k,
        MAX_FILE_SIZE_MB=max_file_size_mb,
    )


# ----------------------------------------------------------------
# Step 4: Create the global settings instance
# ----------------------------------------------------------------
# This runs ONCE when any module does `from config import settings`.
# Python caches module imports, so subsequent imports reuse the
# same instance — this is effectively a Singleton pattern.
settings = _load_settings()


# ----------------------------------------------------------------
# Step 5: Quick verification (runs only when executed directly)
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("📋 AI PDF Chatbot — Configuration")
    print("=" * 60)
    print(f"  API Key:        {'*' * 10}...{settings.GOOGLE_API_KEY[-4:]}")
    print(f"  LLM Model:      {settings.LLM_MODEL_NAME}")
    print(f"  Temperature:    {settings.LLM_TEMPERATURE}")
    print(f"  Embedding:      {settings.EMBEDDING_MODEL_NAME}")
    print(f"  Chunk Size:     {settings.CHUNK_SIZE}")
    print(f"  Chunk Overlap:  {settings.CHUNK_OVERLAP}")
    print(f"  Top-K:          {settings.TOP_K}")
    print(f"  Max File Size:  {settings.MAX_FILE_SIZE_MB} MB")
    print(f"  Base Dir:       {settings.BASE_DIR}")
    print(f"  Upload Dir:     {settings.UPLOAD_DIR}")
    print(f"  Vectorstore:    {settings.VECTORSTORE_DIR}")
    print(f"  Logs Dir:       {settings.LOG_DIR}")
    print("=" * 60)
    print("✅ Configuration loaded successfully!")
