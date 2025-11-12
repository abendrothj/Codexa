"""Data models for Codexa."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Represents a document in the knowledge vault."""

    id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document content")
    file_path: str = Field(..., description="Original file path")
    file_type: str = Field(..., description="File type (md, py, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class IndexRequest(BaseModel):
    """Request model for indexing documents."""

    file_paths: List[str] = Field(..., description="List of file paths to index")
    encrypt: bool = Field(default=False, description="Whether to encrypt content")
    project: Optional[str] = Field(None, description="Project/workspace name (auto-detected or defaults to 'default' if not specified)")


class IndexDirectoryRequest(BaseModel):
    """Request model for indexing a directory."""

    directory_path: str = Field(..., description="Directory path to index")
    extensions: List[str] = Field(default=[".md", ".py"], description="File extensions to index")
    recursive: bool = Field(default=True, description="Whether to search recursively")
    encrypt: bool = Field(default=False, description="Whether to encrypt content")
    project: Optional[str] = Field(None, description="Project/workspace name (auto-detected or defaults to 'default' if not specified)")


class IndexResponse(BaseModel):
    """Response model for index operation."""

    indexed_count: int = Field(..., description="Number of documents indexed")
    failed_count: int = Field(default=0, description="Number of documents that failed")
    document_ids: List[str] = Field(..., description="List of indexed document IDs")
    errors: Optional[List[Dict[str, str]]] = Field(
        default=None, description="List of error details for failed files"
    )


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(default=10, description="Number of results to return (up to 50 for LLM answers to maximize context)")
    offset: int = Field(default=0, description="Number of results to skip (pagination)")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata filters for search"
    )
    project: Optional[str] = Field(None, description="Filter by project/workspace (defaults to current project if not specified)")
    generate_answer: bool = Field(
        default=True, description="Generate intelligent answer using local LLM (RAG). Set to false to disable."
    )
    context_window_override: Optional[int] = Field(
        None,
        description="Override context window for this query (for testing). Must be one of: 4096, 8192, 16384, 32768, 65536, 131072, 262144"
    )


class SearchResult(BaseModel):
    """Individual search result."""

    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    file_path: str = Field(..., description="File path")
    file_type: str = Field(..., description="File type")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response model for search operation."""

    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    answer: Optional[str] = Field(
        default=None, description="Generated intelligent answer (if generate_answer was true)"
    )
    answer_stats: Optional[Dict[str, Any]] = Field(
        None, description="Statistics about LLM answer generation (context usage, tokens, etc.)"
    )


class WebContentRequest(BaseModel):
    """Request model for indexing web content from browser extension."""

    url: str = Field(..., description="Source URL of the content")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Markdown content")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    source: str = Field(default="web", description="Source identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    encrypt: bool = Field(default=False, description="Whether to encrypt content")


class WebContentResponse(BaseModel):
    """Response model for web content indexing."""

    document_id: str = Field(..., description="Indexed document ID")
    status: str = Field(default="indexed", description="Status")
    message: str = Field(..., description="Status message")


class LLMConfigRequest(BaseModel):
    """Request model for LLM configuration."""

    model: str = Field(..., description="Ollama model name")
    base_url: Optional[str] = Field(None, description="Ollama base URL")
    context_window: Optional[int] = Field(
        None,
        description="Context window size in tokens. Must match Ollama's num_ctx setting. "
        "Valid options: 4096, 8192, 16384, 32768, 65536, 131072, 262144. "
        "Default: 4096. Configure in Ollama settings or via OLLAMA_NUM_CTX environment variable."
    )


class DeleteFileRequest(BaseModel):
    """Request model for deleting documents by file path."""

    file_path: str = Field(..., description="Absolute file path to delete")


class DeleteDirectoryRequest(BaseModel):
    """Request model for deleting documents in a directory."""

    directory_path: str = Field(..., description="Absolute directory path")
    recursive: bool = Field(default=True, description="Delete files in subdirectories")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    deleted_count: int = Field(..., description="Number of documents deleted")
    message: str = Field(..., description="Status message")
