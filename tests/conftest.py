"""Pytest configuration and fixtures."""
import pytest


@pytest.fixture(autouse=True)
def cleanup_chroma() -> None:
    """Clean up ChromaDB data after each test."""
    yield
    # Cleanup happens in individual tests as needed
