#!/usr/bin/env python
"""Setup script for Codexa development environment."""
import sys
import subprocess
import os


def run_command(cmd: str, description: str) -> bool:
    """
    Run a shell command.

    Args:
        cmd: Command to run
        description: Description of the command

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}")

    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main() -> None:
    """Main setup process."""
    print("Codexa Development Setup")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

    # Install dependencies
    if not run_command(
        "pip install -r requirements.txt",
        "Installing dependencies..."
    ):
        print("Failed to install dependencies")
        sys.exit(1)

    print("\n✓ Dependencies installed successfully")

    # Install development dependencies
    if not run_command(
        'pip install -e ".[dev]"',
        "Installing development dependencies..."
    ):
        print("Warning: Failed to install development dependencies")

    # Create necessary directories
    os.makedirs("chroma_data", exist_ok=True)
    print("\n✓ Created data directories")

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the API server:")
    print("   uvicorn core.api:app --reload")
    print("\n2. In another terminal, start the desktop app:")
    print("   python desktop/__init__.py")
    print("\n3. Or run batch indexing:")
    print("   python scripts/batch_index.py /path/to/your/project")


if __name__ == "__main__":
    main()
