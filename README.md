# Codexa

> A local-first AI dev knowledge vault with semantic search

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Overview

Codexa is a powerful local-first knowledge management system designed for developers. It enables semantic search over your code, documentation, and notes using state-of-the-art AI embeddings, all while keeping your data completely local and secure.

## Features

- 🔍 **Semantic Search**: Find relevant content using natural language queries
- 🏠 **Local-First**: All data stays on your machine - no cloud services required
- 🔒 **AES-256 Encryption**: Optional encryption for sensitive documents
- 📝 **Multi-Format Support**: Built-in parsers for Markdown (`.md`) and Python (`.py`) files
- 🚀 **Fast API**: RESTful API built with FastAPI for flexible integration
- 🖥️ **Desktop GUI**: User-friendly PySide6 interface for easy interaction
- 🧠 **Smart Embeddings**: Uses SentenceTransformers (`all-MiniLM-L6-v2`) for high-quality semantic understanding
- 💾 **Vector Database**: ChromaDB for efficient similarity search
- 🔧 **Type-Safe**: Full type hints throughout the codebase
- 📦 **Modular Design**: Easy to extend with new file parsers or features
- 🔑 **Optional API Key**: Protect endpoints via `CODEXA_API_KEY`
- 🧱 **Richer Search**: Pagination (`offset`) and metadata filters
- 🛡️ **Encryption Modes**: AES-256-CBC (default) or AES-GCM (AEAD) via `CODEXA_ENC_MODE`
- ⚙️ **Configurable Models**: `CODEXA_MODEL_NAME`, cache and offline mode
- 🤖 **Local LLM (RAG)**: Generate intelligent answers from search results using local transformers models (optional)

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/abendrothj/Codexa.git
cd Codexa

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Codexa

**1. Start the API server:**

```bash
uvicorn core.api:app --reload
```

The API will be available at `http://localhost:8000`

Optionally require an API key:

```bash
export CODEXA_API_KEY="your_secret_key"
uvicorn core.api:app --reload
```

**2. Launch the Desktop GUI:**

In a new terminal:

```bash
python desktop/__init__.py
```

**3. Or use the API directly:**

```bash
# Index files
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CODEXA_API_KEY" \
  -d '{"file_paths": ["/path/to/file.md"]}'

# Search
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CODEXA_API_KEY" \
  -d '{"query": "your search query", "top_k": 10, "offset": 0}'
```

## Architecture

```
┌─────────────────┐
│  Desktop GUI    │  PySide6-based user interface
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   FastAPI API   │  REST API endpoints (/index, /search)
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌──────────┐
│Parsers │ │ Crypto   │  File parsing & AES-256 encryption
└───┬────┘ └────┬─────┘
    │           │
    ↓           ↓
┌──────────────────────┐
│   Vector Database    │  ChromaDB + SentenceTransformers
└──────────────────────┘
```

## Documentation

- [Installation Guide](docs/installation.md)
- [API Documentation](docs/api.md)
- [Usage Guide](docs/usage.md)
- [Architecture Overview](docs/architecture.md)
- [Browser Extension Design](docs/browser_extension.md)

## Project Structure

```
Codexa/
├── core/               # Backend core functionality
│   ├── api/           # FastAPI application and endpoints
│   ├── db/            # ChromaDB integration and vector search
│   ├── models/        # Pydantic data models
│   ├── parsers/       # File parsers (Markdown, Python)
│   └── crypto/        # AES-256 encryption utilities
├── desktop/           # PySide6 desktop GUI application
├── docs/              # Documentation
├── scripts/           # Utility scripts
│   ├── batch_index.py # Batch file indexing
│   └── setup.py       # Development setup script
├── tests/             # Test suite
├── .github/           # CI/CD workflows
├── requirements.txt   # Python dependencies
└── pyproject.toml     # Project configuration
```

## Development

### Setup Development Environment

```bash
python scripts/setup.py
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black core/ desktop/ scripts/
```

### Type Checking

```bash
mypy core/ --ignore-missing-imports
```

### CLI

After an editable install, use the CLI:

```bash
pip install -e .
codexa index /abs/path/file.md
codexa search -q "neural search" --top-k 5 --offset 0
codexa search -q "how does encryption work" --generate-answer  # Generate intelligent answer
codexa delete <document_id>
codexa index-dir /abs/path/project --extensions .md .py
codexa index-web --url "https://example.com" --title "Example" --content "# Markdown" --tag web --meta author=alice
codexa reindex /abs/path/file.md
codexa --help
```

## Use Cases

- **Personal Knowledge Base**: Index your notes, documentation, and code snippets for quick retrieval
- **Project Documentation**: Search across all project files using natural language
- **Code Discovery**: Find relevant code examples and implementations
- **Learning Resources**: Index tutorials and educational materials for easy reference

## Security

- All data processing happens locally on your machine
- Optional AES-256 encryption for sensitive content (CBC by default; set `CODEXA_ENC_MODE=GCM` for AEAD)
- No external API calls or data transmission
- Encryption keys are never stored in the codebase

## Configuration

- Models: `CODEXA_MODEL_NAME`, `CODEXA_MODEL_CACHE`, `CODEXA_OFFLINE=true`
- Auth: `CODEXA_API_KEY` (requires `X-API-Key` header)
- Limits: `CODEXA_MAX_FILES`, `CODEXA_MAX_CONTENT_MB`
- Logging: `CODEXA_LOG_LEVEL`
- LLM (RAG): `CODEXA_ENABLE_LLM=true`, `CODEXA_LLM_MODEL` (default: `microsoft/phi-2`), `CODEXA_LLM_DEVICE` (auto/cpu/cuda/mps)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vector database powered by [ChromaDB](https://www.trychroma.com/)
- Embeddings by [SentenceTransformers](https://www.sbert.net/)
- Desktop GUI with [PySide6](https://doc.qt.io/qtforpython/)

---

Made with ❤️ by the Codexa Contributors