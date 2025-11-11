"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from core.api import app
import tempfile
import os


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Codexa API"
    assert "version" in data


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_index_endpoint(client: TestClient) -> None:
    """Test document indexing."""
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Document\n\nThis is test content.")
        temp_path = f.name

    try:
        response = client.post(
            "/index",
            json={"file_paths": [temp_path], "encrypt": False}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["indexed_count"] == 1
        assert data["failed_count"] == 0
        assert len(data["document_ids"]) == 1
    finally:
        os.unlink(temp_path)


def test_index_nonexistent_file(client: TestClient) -> None:
    """Test indexing non-existent file."""
    response = client.post(
        "/index",
        json={"file_paths": ["/nonexistent/file.md"], "encrypt": False}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["indexed_count"] == 0
    assert data["failed_count"] == 1


def test_search_endpoint(client: TestClient) -> None:
    """Test search endpoint."""
    # First, index a document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Machine Learning\n\nThis document is about neural networks and AI.")
        temp_path = f.name

    try:
        # Index the document
        client.post(
            "/index",
            json={"file_paths": [temp_path], "encrypt": False}
        )

        # Search for it
        response = client.post(
            "/search",
            json={"query": "artificial intelligence", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "artificial intelligence"
        assert "results" in data
        assert data["total_results"] >= 0
    finally:
        os.unlink(temp_path)


def test_search_with_file_type_filter(client: TestClient) -> None:
    """Test search with file type filter."""
    response = client.post(
        "/search",
        json={"query": "test query", "top_k": 5, "file_type": "py"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"


def test_encrypted_indexing_and_search(client: TestClient) -> None:
    """Test indexing and searching encrypted content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Secret Document\n\nThis is sensitive information.")
        temp_path = f.name

    try:
        # Index with encryption
        response = client.post(
            "/index",
            json={"file_paths": [temp_path], "encrypt": True}
        )
        assert response.status_code == 201

        # Search should still work (decryption happens during search)
        response = client.post(
            "/search",
            json={"query": "sensitive information", "top_k": 5}
        )
        assert response.status_code == 200
    finally:
        os.unlink(temp_path)
