"""File parsers for different document types."""
from typing import Dict, Any, Protocol
import os
from pathlib import Path
import frontmatter
import markdown


class FileParser(Protocol):
    """Protocol for file parsers."""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse a file and return content with metadata."""
        ...


class MarkdownParser:
    """Parser for Markdown files."""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a Markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dictionary containing content and metadata
        """
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Convert markdown to plain text for indexing
        html = markdown.markdown(post.content)
        # Simple HTML tag removal for content indexing
        import re

        text = re.sub("<[^<]+?>", "", html)

        return {
            "content": text,
            "raw_content": post.content,
            "metadata": dict(post.metadata) if post.metadata else {},
            "file_type": "md",
            "file_name": os.path.basename(file_path),
        }


class PythonParser:
    """Parser for Python files."""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary containing content and metadata
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract docstrings and comments for better searchability
        import ast

        metadata: Dict[str, Any] = {
            "functions": [],
            "classes": [],
        }

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    metadata["classes"].append(node.name)

            # Extract module docstring
            module_docstring = ast.get_docstring(tree)
            if module_docstring:
                metadata["docstring"] = module_docstring
        except SyntaxError:
            # If parsing fails, still index the raw content
            pass

        return {
            "content": content,
            "metadata": metadata,
            "file_type": "py",
            "file_name": os.path.basename(file_path),
        }


class ParserRegistry:
    """Registry for file parsers."""

    def __init__(self) -> None:
        """Initialize the parser registry."""
        self.parsers: Dict[str, FileParser] = {
            ".md": MarkdownParser(),
            ".py": PythonParser(),
        }

    def get_parser(self, file_path: str) -> FileParser:
        """
        Get appropriate parser for a file.

        Args:
            file_path: Path to the file

        Returns:
            Parser instance

        Raises:
            ValueError: If no parser is available for the file type
        """
        ext = Path(file_path).suffix.lower()
        parser = self.parsers.get(ext)
        if parser is None:
            raise ValueError(f"No parser available for file type: {ext}")
        return parser

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file using the appropriate parser.

        Args:
            file_path: Path to the file

        Returns:
            Parsed content and metadata
        """
        parser = self.get_parser(file_path)
        return parser.parse(file_path)
