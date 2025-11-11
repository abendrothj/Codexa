"""FastAPI application for Codexa knowledge vault."""

from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path

from core.models import (
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from core.db import VectorDatabase
from core.parsers import ParserRegistry
from core.crypto import AESEncryption


# Global instances
db: Optional[VectorDatabase] = None
parser_registry: Optional[ParserRegistry] = None
encryption: Optional[AESEncryption] = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Initialize resources on startup."""
    global db, parser_registry, encryption

    # Initialize database
    db = VectorDatabase()

    # Initialize parser registry
    parser_registry = ParserRegistry()

    # Initialize encryption (load or generate key)
    key_path = os.getenv("CODEXA_KEY_PATH", ".codexa_key")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = AESEncryption.generate_key()
        # Don't auto-save key for security - user should manage it
        print(f"Generated new encryption key. Save it securely!")

    encryption = AESEncryption(key)

    yield

    # Cleanup (if needed)


app = FastAPI(
    title="Codexa API",
    description="Local-first AI dev knowledge vault with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Codexa API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.post("/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def index_documents(request: IndexRequest) -> IndexResponse:
    """
    Index documents into the knowledge vault.

    Args:
        request: Index request with file paths

    Returns:
        Index response with indexed document IDs
    """
    if db is None or parser_registry is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    indexed_ids = []
    failed_count = 0

    for file_path in request.file_paths:
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                failed_count += 1
                continue

            # Parse the file
            parsed = parser_registry.parse_file(file_path)

            # Encrypt content if requested
            content = parsed["content"]
            if request.encrypt:
                content = encryption.encrypt_to_base64(content)
                parsed["metadata"]["encrypted"] = "true"

            # Index the document
            doc_id = db.index_document(
                content=content,
                file_path=file_path,
                metadata={
                    "file_type": parsed["file_type"],
                    "file_name": parsed["file_name"],
                    **parsed["metadata"],
                },
            )
            indexed_ids.append(doc_id)

        except Exception as e:
            print(f"Failed to index {file_path}: {str(e)}")
            failed_count += 1

    return IndexResponse(
        indexed_count=len(indexed_ids),
        failed_count=failed_count,
        document_ids=indexed_ids,
    )


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """
    Search documents using semantic search.

    Args:
        request: Search request with query

    Returns:
        Search response with results
    """
    if db is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    # Build filter if file_type is specified
    filter_metadata = None
    if request.file_type:
        filter_metadata = {"file_type": request.file_type}

    # Perform search
    results = db.search(
        query=request.query,
        top_k=request.top_k,
        filter_metadata=filter_metadata,
    )

    # Format results
    search_results = []
    for result in results:
        content = result["content"]
        metadata = result["metadata"]

        # Decrypt if content was encrypted
        if metadata.get("encrypted") == "true":
            try:
                content = encryption.decrypt_from_base64(content)
            except Exception as e:
                print(f"Failed to decrypt document: {str(e)}")

        search_results.append(
            SearchResult(
                document_id=result["document_id"],
                content=content,
                file_path=metadata.get("file_path", ""),
                file_type=metadata.get("file_type", ""),
                score=result["score"],
                metadata=metadata,
            )
        )

    return SearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
