"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
import tempfile
import os
import contextlib


@pytest.fixture
def client() -> TestClient:
    """Create test client with proper lifecycle."""
    from core.api import app

    # Use context manager to ensure lifespan is triggered
    with TestClient(app) as test_client:
        yield test_client


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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test Document\n\nThis is test content.")
        temp_path = f.name

    try:
        response = client.post("/index", json={"file_paths": [temp_path], "encrypt": False})
        assert response.status_code == 201
        data = response.json()
        assert data["indexed_count"] == 1
        assert data["failed_count"] == 0
        assert len(data["document_ids"]) == 1
    finally:
        os.unlink(temp_path)

def test_api_key_required_for_index(monkeypatch) -> None:
    """Test that API key is enforced when configured."""
    with contextlib.ExitStack() as stack:
        stack.enter_context(monkeypatch.context())
        os.environ["CODEXA_API_KEY"] = "secret"
        from core.api import app
        with TestClient(app) as client:
            # Missing key should fail
            response = client.post("/index", json={"file_paths": [], "encrypt": False})
            assert response.status_code == 401
            # Wrong key should fail
            response = client.post(
                "/index",
                headers={"X-API-Key": "wrong"},
                json={"file_paths": [], "encrypt": False},
            )
            assert response.status_code == 401
            # Correct key should pass (even if no files)
            response = client.post(
                "/index",
                headers={"X-API-Key": "secret"},
                json={"file_paths": [], "encrypt": False},
            )
            assert response.status_code == 201
        del os.environ["CODEXA_API_KEY"]

def test_index_nonexistent_file(client: TestClient) -> None:
    """Test indexing non-existent file."""
    response = client.post(
        "/index", json={"file_paths": ["/nonexistent/file.md"], "encrypt": False}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["indexed_count"] == 0
    assert data["failed_count"] == 1


def test_search_endpoint(client: TestClient) -> None:
    """Test search endpoint."""
    # First, index a document
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Machine Learning\n\nThis document is about neural networks and AI.")
        temp_path = f.name

    try:
        # Index the document
        client.post("/index", json={"file_paths": [temp_path], "encrypt": False})

        # Search for it
        response = client.post("/search", json={"query": "artificial intelligence", "top_k": 5})
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
        "/search", json={"query": "test query", "top_k": 5, "file_type": "py", "offset": 0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"


def test_encrypted_indexing_and_search(client: TestClient) -> None:
    """Test indexing and searching encrypted content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Secret Document\n\nThis is sensitive information.")
        temp_path = f.name

    try:
        # Index with encryption
        response = client.post("/index", json={"file_paths": [temp_path], "encrypt": True})
        assert response.status_code == 201

        # Search should still work (decryption happens during search)
        response = client.post("/search", json={"query": "sensitive information", "top_k": 5})
        assert response.status_code == 200
    finally:
        os.unlink(temp_path)

def test_search_pagination_and_filters(client: TestClient) -> None:
    """Test search pagination and custom filters."""
    # Index two small docs
    paths = []
    for i in range(2):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(f"# Doc {i}\n\napple banana cherry {i}")
            paths.append(f.name)
    try:
        client.post("/index", json={"file_paths": paths, "encrypt": False})
        # Request with offset 1
        response = client.post(
            "/search",
            json={"query": "banana", "top_k": 1, "offset": 1, "filters": {"file_type": "md"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] in (0, 1)
    finally:
        for p in paths:
            os.unlink(p)


def test_delete_document_endpoint(client: TestClient) -> None:
    """Test deleting a document by ID."""
    # Create a temp file and index it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# To Delete\n\nRemove me.")
        temp_path = f.name

    try:
        response = client.post("/index", json={"file_paths": [temp_path], "encrypt": False})
        assert response.status_code == 201
        doc_id = response.json()["document_ids"][0]

        # Delete the document
        del_response = client.delete(f"/documents/{doc_id}")
        assert del_response.status_code == 204
    finally:
        os.unlink(temp_path)
