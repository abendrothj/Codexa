"""Tests for file parsers."""

import pytest
import tempfile
import os
from core.parsers import MarkdownParser, PythonParser, ParserRegistry


def test_markdown_parser() -> None:
    """Test Markdown file parsing."""
    parser = MarkdownParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test Document\n\nThis is a test.")
        temp_path = f.name

    try:
        result = parser.parse(temp_path)
        assert result["file_type"] == "md"
        assert "Test Document" in result["content"]
        assert result["file_name"] == os.path.basename(temp_path)
    finally:
        os.unlink(temp_path)


def test_markdown_with_frontmatter() -> None:
    """Test Markdown parsing with YAML frontmatter."""
    parser = MarkdownParser()

    content = """---
title: Test Document
author: Test Author
---

# Heading

Content here.
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)
        assert result["metadata"]["title"] == "Test Document"
        assert result["metadata"]["author"] == "Test Author"
        assert "Heading" in result["content"]
    finally:
        os.unlink(temp_path)


def test_python_parser() -> None:
    """Test Python file parsing."""
    parser = PythonParser()

    code = '''"""Module docstring."""

def test_function():
    """Function docstring."""
    pass

class TestClass:
    """Class docstring."""
    pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)
        assert result["file_type"] == "py"
        assert "test_function" in result["metadata"]["functions"]
        assert "TestClass" in result["metadata"]["classes"]
        assert result["metadata"]["docstring"] == "Module docstring."
    finally:
        os.unlink(temp_path)


def test_python_parser_invalid_syntax() -> None:
    """Test Python parser with invalid syntax."""
    parser = PythonParser()

    code = "def invalid syntax here"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)
        # Should still return content even with syntax error
        assert result["file_type"] == "py"
        assert result["content"] == code
    finally:
        os.unlink(temp_path)


def test_parser_registry() -> None:
    """Test parser registry."""
    registry = ParserRegistry()

    # Test getting parsers
    md_parser = registry.get_parser("test.md")
    assert isinstance(md_parser, MarkdownParser)

    py_parser = registry.get_parser("test.py")
    assert isinstance(py_parser, PythonParser)

    # Test unsupported file type
    with pytest.raises(ValueError, match="No parser available"):
        registry.get_parser("test.txt")


def test_parse_file_integration() -> None:
    """Test parsing files through registry."""
    registry = ParserRegistry()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test\n\nContent")
        temp_path = f.name

    try:
        result = registry.parse_file(temp_path)
        assert result["file_type"] == "md"
        assert "Test" in result["content"]
    finally:
        os.unlink(temp_path)
