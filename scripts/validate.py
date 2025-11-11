#!/usr/bin/env python
"""
Validation script for Codexa implementation.

This script checks that all required components are present and functional.
"""

import sys
from pathlib import Path


def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING")
        return False


def check_directory_exists(path: str, description: str) -> bool:
    """Check if a directory exists."""
    if Path(path).is_dir():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING")
        return False


def validate_implementation() -> bool:
    """Validate the Codexa implementation."""
    print("=" * 60)
    print("Codexa Implementation Validation")
    print("=" * 60)

    checks = []

    # Core structure
    print("\n## Project Structure")
    checks.append(check_directory_exists("core", "Core package"))
    checks.append(check_directory_exists("desktop", "Desktop package"))
    checks.append(check_directory_exists("docs", "Documentation"))
    checks.append(check_directory_exists("scripts", "Utility scripts"))
    checks.append(check_directory_exists("tests", "Test suite"))
    checks.append(check_directory_exists("examples", "Example files"))

    # Core modules
    print("\n## Core Modules")
    checks.append(check_directory_exists("core/api", "API module"))
    checks.append(check_directory_exists("core/db", "Database module"))
    checks.append(check_directory_exists("core/models", "Models module"))
    checks.append(check_directory_exists("core/parsers", "Parsers module"))
    checks.append(check_directory_exists("core/crypto", "Crypto module"))

    # Key files
    print("\n## Configuration Files")
    checks.append(check_file_exists("requirements.txt", "Requirements file"))
    checks.append(check_file_exists("pyproject.toml", "Project config"))
    checks.append(check_file_exists(".gitignore", "Git ignore file"))
    checks.append(check_file_exists("README.md", "Main README"))

    # Core implementation files
    print("\n## Core Implementation")
    checks.append(check_file_exists("core/api/__init__.py", "FastAPI application"))
    checks.append(check_file_exists("core/db/__init__.py", "ChromaDB integration"))
    checks.append(check_file_exists("core/models/__init__.py", "Pydantic models"))
    checks.append(check_file_exists("core/parsers/__init__.py", "File parsers"))
    checks.append(check_file_exists("core/crypto/__init__.py", "AES-256 encryption"))

    # Desktop GUI
    print("\n## Desktop Application")
    checks.append(check_file_exists("desktop/__init__.py", "PySide6 GUI"))

    # Documentation
    print("\n## Documentation")
    checks.append(check_file_exists("docs/README.md", "Docs index"))
    checks.append(check_file_exists("docs/installation.md", "Installation guide"))
    checks.append(check_file_exists("docs/api.md", "API documentation"))
    checks.append(check_file_exists("docs/usage.md", "Usage guide"))
    checks.append(check_file_exists("docs/architecture.md", "Architecture docs"))

    # Tests
    print("\n## Test Suite")
    checks.append(check_file_exists("tests/test_api.py", "API tests"))
    checks.append(check_file_exists("tests/test_crypto.py", "Crypto tests"))
    checks.append(check_file_exists("tests/test_parsers.py", "Parser tests"))

    # Scripts
    print("\n## Utility Scripts")
    checks.append(check_file_exists("scripts/batch_index.py", "Batch indexing"))
    checks.append(check_file_exists("scripts/setup.py", "Setup script"))

    # CI/CD
    print("\n## CI/CD")
    checks.append(check_file_exists(".github/workflows/ci.yml", "GitHub Actions"))

    # Examples
    print("\n## Example Files")
    checks.append(check_file_exists("examples/python_basics.md", "Python tutorial"))
    checks.append(check_file_exists("examples/fastapi_guide.md", "FastAPI guide"))
    checks.append(check_file_exists("examples/web_scraper.py", "Web scraper"))
    checks.append(check_file_exists("examples/data_processor.py", "Data processor"))

    # Summary
    print("\n" + "=" * 60)
    total = len(checks)
    passed = sum(checks)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n✓ All validation checks passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start API server: uvicorn core.api:app --reload")
        print("3. Launch desktop app: python desktop/__init__.py")
        return True
    else:
        print(f"\n✗ {total - passed} validation checks failed")
        return False


if __name__ == "__main__":
    success = validate_implementation()
    sys.exit(0 if success else 1)
