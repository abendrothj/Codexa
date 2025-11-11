"""CLI tests with mocked httpx.Client."""

import builtins
import contextlib
import io
import sys
from typing import Any, Dict, List, Optional
import types

import pytest

import scripts.cli as cli


class FakeResponse:
    def __init__(self, status_code: int = 200, json_data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> Dict[str, Any]:
        return self._json


class FakeClient:
    def __init__(self, base_url: str, headers: Dict[str, str], timeout: float):
        self.base_url = base_url
        self.headers = headers
        self.timeout = timeout
        self.requests: List[Dict[str, Any]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    # HTTP verbs
    def post(self, path: str, json: Optional[Dict[str, Any]] = None):
        self.requests.append({"method": "POST", "path": path, "json": json})
        # Return minimal expected payloads
        if path == "/index":
            return FakeResponse(201, {"indexed_count": len(json.get("file_paths", [])), "failed_count": 0, "document_ids": ["id-1"]})
        if path == "/index/directory":
            return FakeResponse(201, {"indexed_count": 2, "failed_count": 0, "document_ids": ["id-1", "id-2"]})
        if path == "/reindex":
            return FakeResponse(201, {"indexed_count": len(json.get("file_paths", [])), "failed_count": 0, "document_ids": ["id-9"]})
        if path == "/index/web":
            return FakeResponse(201, {"document_id": "web-1", "status": "indexed", "message": "ok"})
        if path == "/search":
            return FakeResponse(200, {"query": json.get("query"), "results": [], "total_results": 0})
        return FakeResponse(200, {})

    def delete(self, path: str):
        self.requests.append({"method": "DELETE", "path": path})
        return FakeResponse(204, {})


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    # Patch httpx.Client to our FakeClient
    import httpx  # noqa: F401

    def _client(**kwargs):
        return FakeClient(**kwargs)

    monkeypatch.setattr("scripts.cli.httpx.Client", _client)


def run_cli_args(args: List[str]) -> str:
    """Run cli.main() with given args, capture stdout."""
    old_argv = sys.argv
    sys.argv = ["codexa"] + args
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main()
        assert rc == 0
    sys.argv = old_argv
    return buf.getvalue()


def test_cli_index_files() -> None:
    out = run_cli_args(["--base-url", "http://x", "index", "/a.md", "/b.py"])
    assert "201" in out
    assert "indexed_count" in out


def test_cli_index_directory() -> None:
    out = run_cli_args(["index-dir", "/proj", "--extensions", ".md", ".py", "--no-recursive"])
    assert "201" in out
    assert "document_ids" in out


def test_cli_search_filters() -> None:
    out = run_cli_args(
        ["search", "--query", "q", "--top-k", "5", "--offset", "1", "--file-type", "md", "--filter", "source=web"]
    )
    assert "200" in out
    assert '"total_results": 0' in out


def test_cli_delete() -> None:
    out = run_cli_args(["delete", "abc-123"])
    assert "204" in out


def test_cli_index_web() -> None:
    out = run_cli_args(
        [
            "index-web",
            "--url",
            "https://example.com",
            "--title",
            "Example",
            "--content",
            "# Md",
            "--tag",
            "web",
            "--meta",
            "author=alice",
        ]
    )
    assert "201" in out
    assert "web-1" in out


def test_cli_reindex() -> None:
    out = run_cli_args(["reindex", "/a.md"])
    assert "201" in out

