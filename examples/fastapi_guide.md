---
title: FastAPI Quick Start
author: Codexa Team
tags: [fastapi, api, web, python]
---

# FastAPI Quick Start

FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints.

## Installation

```bash
pip install fastapi uvicorn
```

## Creating Your First API

Create a file `main.py`:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## Running the Application

```bash
uvicorn main:app --reload
```

Visit http://localhost:8000 to see your API in action!

## Key Features

- **Fast**: Very high performance, on par with NodeJS and Go
- **Fast to code**: Type hints and automatic validation
- **Easy**: Designed to be easy to use and learn
- **Automatic docs**: Interactive API documentation at `/docs`
- **Standards-based**: Based on OpenAPI and JSON Schema

## Request Body Example

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

@app.post("/items/")
def create_item(item: Item):
    return {"item_name": item.name, "item_price": item.price}
```

## Path Parameters and Validation

```python
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(
    item_id: int = Path(..., title="The ID of the item", ge=1)
):
    return {"item_id": item_id}
```

## Learn More

Check out the official documentation at https://fastapi.tiangolo.com
