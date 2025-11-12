# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication (optional)

- If `CODEXA_API_KEY` is set in the server environment, all write and search endpoints require the header:
  - `X-API-Key: <your_key>`

## Endpoints

### Health Check

**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Index Documents

**POST** `/index`

Index one or more documents into the knowledge vault.

**Request Body:**
```json
{
  "file_paths": ["/path/to/file1.md", "/path/to/file2.py"],
  "encrypt": false
}
```

**Parameters:**
- `file_paths` (array[string], required): List of absolute file paths to index
- `encrypt` (boolean, optional): Whether to encrypt the content (default: false)

**Headers (optional):**
- `X-API-Key`: Required if CODEXA_API_KEY is configured on the server

**Response:**
```json
{
  "indexed_count": 2,
  "failed_count": 0,
  "document_ids": ["uuid-1", "uuid-2"]
}
```

**Status Codes:**
- `201 Created`: Documents successfully indexed
- `413 Payload Too Large`: Too many files (see limits)
- `503 Service Unavailable`: Service not initialized

---

### Index Directory

**POST** `/index/directory`

Index all files in a directory recursively.

**Request Body:**
```json
{
  "directory_path": "/path/to/project",
  "extensions": [".md", ".py"],
  "recursive": true,
  "encrypt": false
}
```

**Parameters:**
- `directory_path` (string, required): Path to the directory to index
- `extensions` (array[string], optional): File extensions to index (default: [".md", ".py"])
- `recursive` (boolean, optional): Whether to search subdirectories (default: true)
- `encrypt` (boolean, optional): Whether to encrypt the content (default: false)

**Headers (optional):**
- `X-API-Key`: Required if CODEXA_API_KEY is configured on the server

**Response:**
```json
{
  "indexed_count": 25,
  "failed_count": 1,
  "document_ids": ["uuid-1", "uuid-2", ...]
}
```

**Status Codes:**
- `201 Created`: Directory indexed successfully
- `400 Bad Request`: Directory not found
- `503 Service Unavailable`: Service not initialized

---

### Index Web Content

**POST** `/index/web`

Index web content from browser extension (HTML converted to Markdown).

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "content": "# Markdown content...",
  "tags": ["web", "documentation"],
  "source": "chrome-extension",
  "metadata": {
    "domain": "example.com",
    "author": "John Doe"
  },
  "encrypt": false
}
```

**Parameters:**
- `url` (string, required): Source URL of the content
- `title` (string, required): Page title
- `content` (string, required): Markdown-formatted content
- `tags` (array[string], optional): Content tags
- `source` (string, optional): Source identifier (default: "web")
- `metadata` (object, optional): Additional metadata
- `encrypt` (boolean, optional): Whether to encrypt the content (default: false)

**Headers (optional):**
- `X-API-Key`: Required if CODEXA_API_KEY is configured on the server

**Response:**
```json
{
  "document_id": "uuid-123",
  "status": "indexed",
  "message": "Web content indexed successfully"
}
```

**Status Codes:**
- `201 Created`: Web content indexed successfully
- `413 Payload Too Large`: Content exceeds size limit (see limits)
- `500 Internal Server Error`: Failed to index content
- `503 Service Unavailable`: Service not initialized

---

### Delete Document

**DELETE** `/documents/{document_id}`

Delete a document by ID.

**Headers (optional):**
- `X-API-Key`: Required if CODEXA_API_KEY is configured on the server

**Status Codes:**
- `204 No Content`: Deleted
- `404 Not Found`: Document not found
- `503 Service Unavailable`: Service not initialized

---

### Reindex Documents

**POST** `/reindex`

Reindex one or more documents (same body as `/index`), creating new IDs.

Headers and responses mirror `/index`.

---

### Search Documents

**POST** `/search`

Perform semantic search over indexed documents.

**Request Body:**
```json
{
  "query": "how to implement authentication",
  "top_k": 10,
  "offset": 0,
  "file_type": "py",
  "filters": {
    "source": "web"
  },
  "generate_answer": false
}
```

**Parameters:**
- `query` (string, required): Search query
- `top_k` (integer, optional): Number of results to return (default: 10)
- `offset` (integer, optional): Skip N results (default: 0)
- `file_type` (string, optional): Filter by file type (e.g., "py", "md")
- `filters` (object, optional): Additional metadata filters
- `generate_answer` (boolean, optional): Generate intelligent answer using local LLM (RAG). Requires `CODEXA_ENABLE_LLM=true` and transformers/torch installed (default: false)

**Headers (optional):**
- `X-API-Key`: Required if CODEXA_API_KEY is configured on the server

**Response:**
```json
{
  "query": "how to implement authentication",
  "results": [
    {
      "document_id": "uuid-1",
      "content": "Document content...",
      "file_path": "/path/to/file.py",
      "file_type": "py",
      "score": 0.85,
      "metadata": {
        "file_name": "file.py",
        "functions": ["authenticate", "login"]
      }
    }
  ],
  "total_results": 1,
  "answer": "Based on the indexed documents, authentication can be implemented using..."
}
```

**Response Fields:**
- `answer` (string, optional): Generated intelligent answer when `generate_answer=true`. Only present if LLM is enabled and available.

**Status Codes:**
- `200 OK`: Search successful
- `503 Service Unavailable`: Service not initialized

---

## Examples

### Index Files with cURL

```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CODEXA_API_KEY" \
  -d '{
    "file_paths": ["/home/user/docs/readme.md", "/home/user/code/main.py"],
    "encrypt": false
  }'
```

### Search with cURL

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CODEXA_API_KEY" \
  -d '{
    "query": "authentication implementation",
    "top_k": 5
  }'
```

### Using Python

```python
import httpx

# Index files
response = httpx.post(
    "http://localhost:8000/index",
    headers={"X-API-Key": "your_key"},
    json={
        "file_paths": ["/path/to/file.md"],
        "encrypt": False
    }
)
print(response.json())

# Search
response = httpx.post(
    "http://localhost:8000/search",
    headers={"X-API-Key": "your_key"},
    json={
        "query": "search query",
        "top_k": 10,
        "offset": 0,
        "filters": {"file_type": "md"}
    }
)
print(response.json())
```

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Limits and configuration

- Request limits:
  - `CODEXA_MAX_FILES` (default: 200) limits number of files in `/index`.
  - `CODEXA_MAX_CONTENT_MB` (default: 5) limits `/index/web` content size.
- Authentication:
  - `CODEXA_API_KEY` enables API key requirement; clients must send `X-API-Key`.
- Embedding model:
  - `CODEXA_MODEL_NAME` (default: `all-MiniLM-L6-v2`)
  - `CODEXA_MODEL_CACHE` (directory for model cache)
  - `CODEXA_OFFLINE=true` to disable internet access and use local cache only.
- Encryption:
  - `CODEXA_ENC_MODE=GCM` to use AES-GCM (AEAD). Default is CBC.
