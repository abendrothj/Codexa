# Usage Guide

## Getting Started

### 1. Start the Backend

First, start the FastAPI server:

```bash
uvicorn core.api:app --reload
```

### 2. Index Your Documents

Use the desktop app or API to index your files:

#### Using Desktop App

1. Launch the desktop application
2. Click "Index Files" button
3. Select the `.md` or `.py` files you want to index
4. Wait for indexing to complete

#### Using API

```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "/path/to/your/docs/readme.md",
      "/path/to/your/code/main.py"
    ]
  }'
```

### 3. Search Your Knowledge Base

#### Using Desktop App

1. Enter your search query in the search box
2. Press Enter or click "Search"
3. Browse results in the left panel
4. Click on a result to view full content

#### Using API

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "top_k": 10
  }'
```

## Advanced Features

### Encrypting Content

Enable encryption when indexing sensitive documents:

```python
import httpx

response = httpx.post(
    "http://localhost:8000/index",
    json={
        "file_paths": ["/path/to/sensitive.md"],
        "encrypt": True
    }
)
```

**Note**: Make sure to securely store your encryption key. Set `CODEXA_KEY_PATH` environment variable to use a persistent key.

### Filtering by File Type

Search only specific file types:

```python
response = httpx.post(
    "http://localhost:8000/search",
    json={
        "query": "authentication",
        "top_k": 5,
        "file_type": "py"  # Only search Python files
    }
)
```

### Batch Indexing

Use the provided script to index entire directories:

```bash
python scripts/batch_index.py /path/to/your/project
```

## Use Cases

### 1. Personal Documentation Vault

Index your personal notes, documentation, and code snippets. Search across all your files using natural language.

### 2. Project Knowledge Base

Index all documentation and code in a project. Quickly find relevant implementations or documentation.

### 3. Learning Resource

Index tutorials, blog posts, and code examples. Search to find relevant learning materials.

## Tips

- **Better Search Results**: Use descriptive queries. Instead of "login", try "how to implement user authentication"
- **Regular Indexing**: Re-index files after making significant changes
- **Organize Files**: Keep related files together for better context in search results
- **Use Metadata**: Python file parser extracts functions and classes automatically for better searchability

## Troubleshooting

### API Not Starting

- Check if port 8000 is available
- Verify Python dependencies are installed
- Check console for error messages

### No Search Results

- Ensure files are indexed first
- Verify the API server is running
- Check if the query matches content in indexed files

### Desktop App Connection Error

- Ensure the API server is running at `http://localhost:8000`
- Check firewall settings
- Verify network connectivity

### Slow Search Performance

- Reduce `top_k` value for faster results
- Consider indexing fewer files
- Check system resources (CPU, memory)
