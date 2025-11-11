# Installation Guide

## Prerequisites

- Python 3.9 or higher
- pip package manager

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/abendrothj/Codexa.git
cd Codexa
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e ".[dev]"
```

**Note**: On first run, the SentenceTransformer model (`all-MiniLM-L6-v2`) will be downloaded from HuggingFace (~80MB). This requires an internet connection and may take a few minutes.

## Running the Application

### Start the API Server

```bash
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Start the Desktop Application

In a new terminal (with the API server running):

```bash
python -m desktop
```

Or run directly:

```bash
python desktop/__init__.py
```

## Configuration

### Encryption Key

By default, Codexa generates a new encryption key on startup. To use a persistent key:

1. Set the `CODEXA_KEY_PATH` environment variable:
   ```bash
   export CODEXA_KEY_PATH=/path/to/your/key.bin
   ```

2. Generate a key manually (if needed):
   ```python
   from core.crypto import AESEncryption
   key = AESEncryption.generate_key()
   with open('your_key.bin', 'wb') as f:
       f.write(key)
   ```

### Database Location

The ChromaDB database is stored in `./chroma_data` by default. This can be changed in the code if needed.

## Verification

Test that the API is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```
