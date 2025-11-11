# Codexa Examples

This directory contains example files that demonstrate various programming concepts and can be used to test Codexa's indexing and search capabilities.

## Files

- **python_basics.md** - Introduction to Python programming fundamentals
- **fastapi_guide.md** - Quick start guide for FastAPI web framework
- **web_scraper.py** - Example web scraping implementation
- **data_processor.py** - Data processing with pandas

## How to Use

### Index the Examples

Using the batch indexing script:

```bash
python scripts/batch_index.py examples/
```

Or through the API:

```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "examples/python_basics.md",
      "examples/fastapi_guide.md",
      "examples/web_scraper.py",
      "examples/data_processor.py"
    ]
  }'
```

### Search Examples

Try these search queries:

1. "How to create a web API"
2. "Python data types and variables"
3. "Scraping HTML content"
4. "Processing tabular data"
5. "FastAPI request validation"

### Using the Desktop App

1. Start the API server: `uvicorn core.api:app --reload`
2. Launch the desktop app: `python desktop/__init__.py`
3. Click "Index Files" and select files from the examples folder
4. Enter search queries to find relevant content

## Adding Your Own Examples

Feel free to add more example files in supported formats (`.md`, `.py`) to expand the knowledge base.
