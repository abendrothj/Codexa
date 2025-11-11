# API Documentation

## Base URL

```
http://localhost:8000
```

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
- `503 Service Unavailable`: Service not initialized

---

### Search Documents

**POST** `/search`

Perform semantic search over indexed documents.

**Request Body:**
```json
{
  "query": "how to implement authentication",
  "top_k": 10,
  "file_type": "py"
}
```

**Parameters:**
- `query` (string, required): Search query
- `top_k` (integer, optional): Number of results to return (default: 10)
- `file_type` (string, optional): Filter by file type (e.g., "py", "md")

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
  "total_results": 1
}
```

**Status Codes:**
- `200 OK`: Search successful
- `503 Service Unavailable`: Service not initialized

---

## Examples

### Index Files with cURL

```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["/home/user/docs/readme.md", "/home/user/code/main.py"],
    "encrypt": false
  }'
```

### Search with cURL

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
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
    json={
        "file_paths": ["/path/to/file.md"],
        "encrypt": False
    }
)
print(response.json())

# Search
response = httpx.post(
    "http://localhost:8000/search",
    json={
        "query": "search query",
        "top_k": 10
    }
)
print(response.json())
```

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
