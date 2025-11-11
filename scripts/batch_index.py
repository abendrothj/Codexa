#!/usr/bin/env python
"""Batch indexing script for Codexa."""
import sys
import os
from pathlib import Path
from typing import List
import httpx


def find_files(directory: str, extensions: List[str]) -> List[str]:
    """
    Recursively find files with specified extensions.

    Args:
        directory: Root directory to search
        extensions: List of file extensions (e.g., ['.md', '.py'])

    Returns:
        List of file paths
    """
    files = []
    path = Path(directory)

    for ext in extensions:
        files.extend([str(f) for f in path.rglob(f"*{ext}")])

    return files


def index_files(file_paths: List[str], api_url: str = "http://localhost:8000") -> None:
    """
    Index files using the Codexa API.

    Args:
        file_paths: List of file paths to index
        api_url: API base URL
    """
    print(f"Indexing {len(file_paths)} files...")

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{api_url}/index",
                json={"file_paths": file_paths, "encrypt": False},
            )
            response.raise_for_status()
            result = response.json()

            print(f"✓ Indexed: {result['indexed_count']} files")
            if result["failed_count"] > 0:
                print(f"✗ Failed: {result['failed_count']} files")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python batch_index.py <directory> [api_url]")
        print("Example: python batch_index.py /path/to/project http://localhost:8000")
        sys.exit(1)

    directory = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    # Find supported files
    extensions = [".md", ".py"]
    file_paths = find_files(directory, extensions)

    if not file_paths:
        print(f"No files found with extensions: {extensions}")
        sys.exit(0)

    print(f"Found {len(file_paths)} files in {directory}")

    # Index files
    index_files(file_paths, api_url)


if __name__ == "__main__":
    main()
