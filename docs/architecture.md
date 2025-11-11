# Architecture

## Overview

Codexa is built with a modular architecture separating concerns into distinct layers:

```
┌─────────────────┐
│  Desktop GUI    │  PySide6-based user interface
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   FastAPI API   │  REST API endpoints
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌──────────┐
│Parsers │ │ Crypto   │  File parsing & encryption
└───┬────┘ └────┬─────┘
    │           │
    ↓           ↓
┌──────────────────────┐
│   Vector Database    │  ChromaDB + SentenceTransformers
└──────────────────────┘
```

## Components

### Core Package (`/core`)

The backend logic organized into modules:

#### API (`core/api`)
- FastAPI application
- REST endpoints for indexing and search
- Request/response validation
- Lifecycle management

#### Models (`core/models`)
- Pydantic models for type safety
- Request and response schemas
- Document representations

#### Database (`core/db`)
- ChromaDB integration
- Vector storage and retrieval
- Embedding generation using SentenceTransformers
- Semantic search implementation

#### Parsers (`core/parsers`)
- Extensible file parser system
- Markdown parser (with frontmatter support)
- Python parser (with AST analysis)
- Easy to add new file types

#### Crypto (`core/crypto`)
- AES-256 encryption/decryption
- Key management utilities
- Secure content storage

### Desktop Package (`/desktop`)

PySide6-based GUI application:
- Search interface
- Results display
- File indexing dialog
- Asynchronous operations using QThread
- Clean, modern UI

### Documentation (`/docs`)

Comprehensive documentation:
- Installation guide
- API reference
- Usage examples
- Architecture overview

### Scripts (`/scripts`)

Utility scripts for common tasks:
- Batch indexing
- Database management
- Setup automation

## Data Flow

### Indexing Flow

1. **File Selection**: User selects files via GUI or API
2. **Parsing**: Appropriate parser extracts content and metadata
3. **Encryption** (optional): Content encrypted with AES-256
4. **Embedding**: SentenceTransformer generates vector embedding
5. **Storage**: ChromaDB stores document with embedding
6. **Response**: Document IDs returned to user

### Search Flow

1. **Query Input**: User enters natural language query
2. **Embedding**: Query converted to vector embedding
3. **Vector Search**: ChromaDB performs similarity search
4. **Decryption** (if needed): Encrypted content decrypted
5. **Ranking**: Results sorted by similarity score
6. **Display**: Results presented to user

## Technologies

### Backend
- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **ChromaDB**: Vector database for similarity search
- **SentenceTransformers**: Embedding model (`all-MiniLM-L6-v2`)
- **Cryptography**: AES-256 encryption

### Frontend
- **PySide6**: Qt for Python, cross-platform GUI
- **QThread**: Asynchronous operations

### File Processing
- **python-frontmatter**: YAML frontmatter parsing
- **markdown**: Markdown to HTML conversion
- **ast**: Python code analysis

## Design Principles

### Modularity
Each component has a single responsibility and can be tested independently.

### Type Safety
Full type hints throughout the codebase with mypy support.

### Local-First
All data processing happens locally. No external API calls required.

### Security
Optional encryption for sensitive content. Keys never stored in code.

### Extensibility
Easy to add new file parsers, embedding models, or storage backends.

## Future Enhancements

- Support for more file types (Java, JavaScript, etc.)
- Advanced filtering and faceted search
- Document versioning and history
- Multi-language support
- Plugin system for custom parsers
- Distributed search across multiple vaults
