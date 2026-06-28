"""
RAG Chain Module
================

Builds and runs the Retrieval-Augmented Generation (RAG) pipeline.

How RAG works:
    1. User asks a question.
    2. The question is embedded and used to search the FAISS index.
    3. Top-K most relevant document chunks are retrieved.
    4. The chunks + question are sent to Gemini as a prompt.
    5. Gemini generates an answer grounded in the retrieved context.

This approach ensures the LLM's answers are FACTUAL and based on
the actual PDF content, rather than hallucinated from training data.

Usage:
    from utils.rag_chain import get_answer

    answer = get_answer(vector_store, "What is the main topic?")
    print(answer)
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# --- Prompt Template ---
# This template instructs Gemini to:
# 1. Only use the provided context (no hallucination).
# 2. Admit when it doesn't know the answer.
# 3. Provide clear, structured responses.
RAG_PROMPT_TEMPLATE = """You are a helpful AI assistant that answers questions based on the provided PDF document content.

Use ONLY the following context to answer the question. If the answer is not found in the context, say "I couldn't find the answer to that in the uploaded document."

Context from the PDF:
{context}

Question: {question}

Instructions:
- Answer based ONLY on the provided context above.
- If the context doesn't contain enough information, clearly state that.
- Be concise but thorough.
- Use bullet points or numbered lists when appropriate.
- If quoting from the document, use quotation marks.

Answer:"""

RAG_PROMPT = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)


def _create_llm() -> ChatGoogleGenerativeAI:
    """
    Create a configured Gemini LLM instance.

    Returns:
        ChatGoogleGenerativeAI: Configured Gemini model.
    """
    logger.info(
        f"Initializing LLM: {settings.LLM_MODEL_NAME} "
        f"(temperature={settings.LLM_TEMPERATURE})"
    )

    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        convert_system_message_to_human=True,
    )


def _format_docs(docs):
    """Format retrieved documents into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def get_answer(vector_store: FAISS, question: str) -> str:
    """
    Run the RAG pipeline: retrieve relevant chunks and generate an answer.

    Uses LangChain Expression Language (LCEL) to build a modern
    retrieval chain: retriever → prompt → LLM → output parser.

    Args:
        vector_store: FAISS vector store containing embedded document chunks.
        question: The user's question string.

    Returns:
        str: The generated answer grounded in the PDF content.

    Raises:
        ValueError: If question is empty.
        Exception: If LLM call fails.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    logger.info(f"RAG query: '{question[:80]}...'")

    llm = _create_llm()

    # Build retriever
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.TOP_K},
    )

    # Build LCEL chain: retrieve docs → format → prompt → LLM → parse
    rag_chain = (
        {
            "context": retriever | _format_docs,
            "question": RunnablePassthrough(),
        }
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    try:
        answer = rag_chain.invoke(question)

        logger.info(f"Answer generated ({len(answer)} chars)")

        return answer

    except Exception as e:
        logger.error(f"RAG chain failed: {e}")
        raise
