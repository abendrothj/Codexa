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


class IndexDirectoryRequest(BaseModel):
    """Request model for indexing a directory."""

    directory_path: str = Field(..., description="Directory path to index")
    extensions: List[str] = Field(default=[".md", ".py"], description="File extensions to index")
    recursive: bool = Field(default=True, description="Whether to search recursively")
    encrypt: bool = Field(default=False, description="Whether to encrypt content")


class IndexResponse(BaseModel):
    """Response model for index operation."""

    indexed_count: int = Field(..., description="Number of documents indexed")
    failed_count: int = Field(default=0, description="Number of documents that failed")
    document_ids: List[str] = Field(..., description="List of indexed document IDs")


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(default=10, description="Number of results to return")
    offset: int = Field(default=0, description="Number of results to skip (pagination)")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata filters for search"
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
