"""FastAPI application for Codexa knowledge vault."""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi import Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path
import logging

from core.models import (
    IndexRequest,
    IndexDirectoryRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    WebContentRequest,
    WebContentResponse,
    LLMConfigRequest,
    DeleteFileRequest,
    DeleteDirectoryRequest,
    DeleteResponse,
)
from core.db import VectorDatabase
from core.parsers import ParserRegistry
from core.crypto import AESEncryption
from core.config import get_llm_config, set_llm_config, get_current_project, add_usage_entry, get_smart_recommendation

# LLM import (Ollama)
try:
    from core.llm import OllamaLLM
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    OllamaLLM = None  # type: ignore


# Global instances
db: Optional[VectorDatabase] = None
parser_registry: Optional[ParserRegistry] = None
encryption: Optional[AESEncryption] = None
llm: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Initialize resources on startup."""
    global db, parser_registry, encryption, llm

    # Initialize database
    db = VectorDatabase()

    # Initialize parser registry
    parser_registry = ParserRegistry()

    # Initialize encryption (load or generate key)
    key_path = os.getenv("CODEXA_KEY_PATH", ".codexa_key")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = AESEncryption.generate_key()
        # Don't auto-save key for security - user should manage it
        logger.info("Generated new encryption key. Save it securely!")

    encryption = AESEncryption(key)

    # Initialize LLM (Ollama) - default enabled, can be disabled with CODEXA_DISABLE_LLM=true
    if LLM_AVAILABLE and os.getenv("CODEXA_DISABLE_LLM", "false").lower() != "true":
        try:
            # Get config from file or env vars (env vars take precedence)
            llm_config = get_llm_config()
            model_name = llm_config["model"]
            base_url = llm_config["base_url"]
            context_window = llm_config.get("context_window", 4096)
            logger.info(f"Initializing Ollama LLM: {model_name} at {base_url} (context_window={context_window})")
            logger.info(
                f"Note: Ensure Ollama's num_ctx is set to {context_window}. "
                f"Configure in Ollama settings or via: OLLAMA_NUM_CTX={context_window}"
            )
            llm = OllamaLLM(model_name=model_name, base_url=base_url, context_window=context_window)
            # Initialize to resolve model name (handles :latest tags)
            try:
                if not llm._initialized:
                    llm._initialize()
                # Update config with resolved name if it changed
                resolved_model = llm.model_name
                if resolved_model != model_name:
                    logger.info(f"Model name resolved: {model_name} -> {resolved_model}")
                    set_llm_config(resolved_model, base_url, context_window)
                
                if llm.is_available():
                    logger.info("Ollama LLM initialized successfully")
                else:
                    logger.warning("Ollama connection failed. Make sure Ollama is running: ollama serve")
                    llm = None
            except Exception as e:
                logger.warning(f"Failed to initialize LLM during startup: {e}")
                llm = None
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}. Answer generation will be disabled.")
            logger.info("To use LLM features, install Ollama: https://ollama.ai and run: ollama pull llama3.2")
            llm = None
    else:
        llm = None
        if not LLM_AVAILABLE:
            logger.info("LLM not available (httpx not installed). Install with: pip install httpx")

    yield

    # Cleanup (if needed)


app = FastAPI(
    title="Codexa API",
    description="Local-first AI dev knowledge vault with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure basic structured logging
logging.basicConfig(
    level=os.getenv("CODEXA_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("codexa")

def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Optional API key enforcement if CODEXA_API_KEY is set."""
    required = os.getenv("CODEXA_API_KEY")
    if not required:
        return
    if not x_api_key or x_api_key != required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Codexa API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.post("/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def index_documents(request: IndexRequest) -> IndexResponse:
    """
    Index documents into the knowledge vault.

    Args:
        request: Index request with file paths

    Returns:
        Index response with indexed document IDs
    """
    if db is None or parser_registry is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    indexed_ids = []
    failed_count = 0
    errors: List[Dict[str, str]] = []

    # Request limits
    max_files = int(os.getenv("CODEXA_MAX_FILES", "200"))
    if len(request.file_paths) > max_files:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files; limit is {max_files}",
        )

    # Determine project once (mandatory - use request project or auto-detect/create default)
    project = request.project
    if project is None:
        project = get_current_project()  # Always returns a project (creates default if needed)
    
    # Prepare documents for batch indexing
    documents_to_index: List[Dict[str, Any]] = []
    
    # Parse files in parallel for better performance
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    
    def parse_file_safe(file_path: str) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
        """Parse a file and return (file_path, parsed_data, error)."""
        abs_file_path = os.path.abspath(file_path)
        try:
            # Check if file exists
            if not os.path.exists(abs_file_path):
                return (abs_file_path, None, f"File not found: {abs_file_path}")
            
            # Parse the file
            parsed = parser_registry.parse_file(abs_file_path)
            
            # Encrypt content if requested
            content = parsed["content"]
            if request.encrypt:
                content = encryption.encrypt_to_base64(content)
                parsed["metadata"]["encrypted"] = "true"
            
            # Prepare metadata
            metadata = {
                "file_type": parsed["file_type"],
                "file_name": parsed["file_name"],
                "project": project,  # Always include project
                **parsed["metadata"],
            }
            
            return (abs_file_path, {
                "content": content,
                "file_path": abs_file_path,
                "metadata": metadata,
            }, None)
        except Exception as e:
            error_msg = f"Failed to parse: {str(e)}"
            logger.exception("Failed to parse file", extra={"file_path": abs_file_path})
            return (abs_file_path, None, error_msg)
    
    # Parse files in parallel (use ThreadPoolExecutor for I/O-bound operations)
    max_workers = min(int(os.getenv("CODEXA_INDEX_WORKERS", "4")), len(request.file_paths), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(parse_file_safe, file_path): file_path
            for file_path in request.file_paths
        }
        
        for future in as_completed(future_to_path):
            file_path, parsed_data, error = future.result()
            if error:
                failed_count += 1
                errors.append({"file_path": file_path, "error": error})
            elif parsed_data:
                documents_to_index.append(parsed_data)
    
    # Batch index all successfully parsed documents
    if documents_to_index:
        try:
            indexed_ids = db.index_documents(documents_to_index, batch_size=100)
        except Exception as e:
            logger.exception("Failed to batch index documents")
            # Fallback to individual indexing
            for doc in documents_to_index:
                try:
                    doc_id = db.index_document(
                        content=doc["content"],
                        file_path=doc["file_path"],
                        metadata=doc["metadata"],
                    )
                    indexed_ids.append(doc_id)
                except Exception as e2:
                    logger.exception("Failed to index document in fallback", extra={"file_path": doc["file_path"]})
                    failed_count += 1
                    errors.append({"file_path": doc["file_path"], "error": f"Failed to index: {str(e2)}"})

    return IndexResponse(
        indexed_count=len(indexed_ids),
        failed_count=failed_count,
        document_ids=indexed_ids,
        errors=errors if errors else None,
    )


@app.post("/index/directory", response_model=IndexResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def index_directory(request: IndexDirectoryRequest) -> IndexResponse:
    """
    Index all files in a directory recursively.

    Args:
        request: Directory index request

    Returns:
        Index response with indexed document IDs
    """
    if db is None or parser_registry is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    # Resolve relative directory path to absolute path
    abs_directory_path = os.path.abspath(request.directory_path)
    
    # Validate directory exists
    if not os.path.isdir(abs_directory_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory not found: {abs_directory_path}",
        )

    # Determine project (mandatory - use request project or auto-detect/create default)
    project = request.project
    if project is None:
        project = get_current_project()  # Always returns a project (creates default if needed)
    
    # Find all files with specified extensions
    from pathlib import Path

    file_paths = []
    path = Path(abs_directory_path)

    if request.recursive:
        for ext in request.extensions:
            file_paths.extend([str(f) for f in path.rglob(f"*{ext}")])
    else:
        for ext in request.extensions:
            file_paths.extend([str(f) for f in path.glob(f"*{ext}")])

    if not file_paths:
        return IndexResponse(indexed_count=0, failed_count=0, document_ids=[])

    # Prepare documents for batch indexing
    documents_to_index: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    
    # Parse files in parallel for better performance
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def parse_file_safe(file_path: str) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
        """Parse a file and return (file_path, parsed_data, error)."""
        try:
            # Parse the file
            parsed = parser_registry.parse_file(file_path)
            
            # Encrypt content if requested
            content = parsed["content"]
            if request.encrypt:
                content = encryption.encrypt_to_base64(content)
                parsed["metadata"]["encrypted"] = "true"
            
            # Prepare metadata
            metadata = {
                "file_type": parsed["file_type"],
                "file_name": parsed["file_name"],
                "project": project,  # Always include project
                **parsed["metadata"],
            }
            
            return (file_path, {
                "content": content,
                "file_path": file_path,
                "metadata": metadata,
            }, None)
        except Exception as e:
            error_msg = f"Failed to parse: {str(e)}"
            logger.exception("Failed to parse file in directory", extra={"file_path": file_path})
            return (file_path, None, error_msg)
    
    # Parse files in parallel
    max_workers = min(int(os.getenv("CODEXA_INDEX_WORKERS", "4")), len(file_paths), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(parse_file_safe, file_path): file_path
            for file_path in file_paths
        }
        
        for future in as_completed(future_to_path):
            file_path, parsed_data, error = future.result()
            if error:
                errors.append({"file_path": file_path, "error": error})
            elif parsed_data:
                documents_to_index.append(parsed_data)
    
    # Batch index all successfully parsed documents
    indexed_ids = []
    failed_count = len(errors)
    if documents_to_index:
        try:
            indexed_ids = db.index_documents(documents_to_index, batch_size=100)
        except Exception as e:
            logger.exception("Failed to batch index documents in directory")
            # Fallback to individual indexing
            for doc in documents_to_index:
                try:
                    doc_id = db.index_document(
                        content=doc["content"],
                        file_path=doc["file_path"],
                        metadata=doc["metadata"],
                    )
                    indexed_ids.append(doc_id)
                except Exception as e2:
                    logger.exception("Failed to index document in fallback", extra={"file_path": doc["file_path"]})
                    failed_count += 1
                    errors.append({"file_path": doc["file_path"], "error": f"Failed to index: {str(e2)}"})

    return IndexResponse(
        indexed_count=len(indexed_ids),
        failed_count=failed_count,
        document_ids=indexed_ids,
        errors=errors if errors else None,
    )


@app.post("/index/web", response_model=WebContentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def index_web_content(request: WebContentRequest) -> WebContentResponse:
    """
    Index web content from browser extension.

    Args:
        request: Web content request with URL, title, and content

    Returns:
        Web content response with document ID
    """
    if db is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        # Content size limit (MB)
        max_mb = int(os.getenv("CODEXA_MAX_CONTENT_MB", "5"))
        if len(request.content.encode("utf-8")) > max_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Content too large; limit is {max_mb}MB",
            )
        # Determine project (mandatory - auto-detect/create default)
        project = get_current_project()  # Always returns a project (creates default if needed)
        
        # Prepare metadata
        metadata = {
            "url": request.url,
            "title": request.title,
            "tags": request.tags,
            "source": request.source,
            "file_type": "web",
            "project": project,  # Always include project
            **request.metadata,
        }

        # Encrypt content if requested
        content = request.content
        if request.encrypt:
            content = encryption.encrypt_to_base64(content)
            metadata["encrypted"] = "true"

        # Index the web content
        doc_id = db.index_document(
            content=content,
            file_path=request.url,  # Use URL as file_path for web content
            metadata=metadata,
        )

        return WebContentResponse(
            document_id=doc_id,
            status="indexed",
            message="Web content indexed successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index web content: {str(e)}",
        )


@app.post("/search", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def search_documents(request: SearchRequest) -> SearchResponse:
    """
    Search documents using semantic search.

    Args:
        request: Search request with query

    Returns:
        Search response with results
    """
    if db is None or encryption is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    # Build filters
    filter_metadata = {}
    if request.file_type:
        filter_metadata["file_type"] = request.file_type
    if request.filters:
        filter_metadata.update(request.filters)
    
    # Handle project filter (mandatory - always filter by project)
    project_filter = request.project
    if project_filter is None:
        # If not specified, use current project from config (always returns a project)
        project_filter = get_current_project()
    
    # Always filter by project (no global option)
    filter_metadata["project"] = project_filter
    
    if not filter_metadata:
        filter_metadata = None

    # Perform search
    # For LLM answers, use more results to provide comprehensive context
    # Ollama supports up to 256k tokens, so we can use much more context
    search_top_k = request.top_k
    if request.generate_answer and llm is not None:
        # Use more results for LLM (up to 50) to provide comprehensive context
        search_top_k = max(request.top_k, 50)
    
    results = db.search(
        query=request.query,
        top_k=search_top_k,
        filter_metadata=filter_metadata,
        offset=request.offset,
    )

    logger.info(f"Search returned {len(results)} results for query: '{request.query}' (project: {project_filter})")

    # Format results
    search_results = []
    for result in results:
        content = result["content"]
        metadata = result["metadata"]
        
        # All documents have projects now, so no filtering needed here

        # Decrypt if content was encrypted
        if metadata.get("encrypted") == "true":
            try:
                content = encryption.decrypt_from_base64(content)
            except Exception as e:
                logger.exception("Failed to decrypt document", extra={"document_id": result.get("document_id")})

        search_results.append(
            SearchResult(
                document_id=result["document_id"],
                content=content,
                file_path=metadata.get("file_path", ""),
                file_type=metadata.get("file_type", ""),
                score=result["score"],
                metadata=metadata,
            )
        )

    # Generate intelligent answer if requested and LLM is available
    answer: Optional[str] = None
    answer_stats: Optional[Dict[str, Any]] = None
    if request.generate_answer:
        if llm is not None and hasattr(llm, "is_available") and llm.is_available():
            try:
                if not search_results:
                    logger.warning(f"No search results found for query: '{request.query}' (project: {project_filter})")
                    answer = (
                        f"I couldn't find any indexed documents matching your query '{request.query}' "
                        f"in the current project '{project_filter}'. "
                        f"Please make sure you have indexed some files first using the index endpoint, "
                        f"or try a different search query."
                    )
                    answer_stats = {
                        "context_documents_available": 0,
                        "context_documents_used": 0,
                        "context_usage_percent": 0,
                        "warning": "No documents found in search results"
                    }
                else:
                    logger.info(f"Generating intelligent answer using local LLM with {len(search_results)} search results")
                    context_list = [
                        {
                            "content": r.content,
                            "file_path": r.file_path,
                            "score": r.score,
                            "file_type": r.file_type,  # Include file type for code-aware processing
                        }
                        for r in search_results
                    ]
                    logger.debug(f"Context list has {len(context_list)} items, first item content length: {len(context_list[0].get('content', '')) if context_list else 0}")
                    answer_result = llm.generate_answer(
                        query=request.query,
                        context=context_list,
                        context_window_override=request.context_window_override,
                    )
                # Handle both old format (str) and new format (tuple[str, dict])
                if isinstance(answer_result, tuple):
                    answer, answer_stats = answer_result
                    # Track usage history for smart recommendations
                    if answer_stats and "context_usage_percent" in answer_stats:
                        try:
                            add_usage_entry(answer_stats)
                        except Exception:
                            pass  # Don't fail if history tracking fails
                else:
                    answer = answer_result
                    answer_stats = {}
            except Exception as e:
                logger.exception("Failed to generate answer", extra={"error": str(e)})
                answer = f"Error generating answer: {str(e)}"
                answer_stats = {"error": str(e)}
        else:
            answer = "LLM not available. Make sure Ollama is running (ollama serve) and the model is installed (ollama pull llama3.2)."
            answer_stats = {}

    return SearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
        answer=answer,
        answer_stats=answer_stats,
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/config/llm", dependencies=[Depends(verify_api_key)])
async def update_llm_config(request: LLMConfigRequest) -> dict[str, Any]:
    """
    Update LLM configuration and reload.
    
    Args:
        request: LLM configuration request
    
    Returns:
        Updated configuration
    """
    global llm
    
    try:
        # Get current config and merge with request
        current_config = get_llm_config()
        model_name = request.model
        base_url_val = request.base_url or current_config["base_url"]
        context_window_val = request.context_window or current_config.get("context_window", 4096)
        
        # Save to config file
        set_llm_config(model_name, base_url_val, context_window_val)
        
        # Reinitialize LLM
        if LLM_AVAILABLE:
            logger.info(f"Reloading Ollama LLM: {model_name} at {base_url_val} (context_window={context_window_val})")
            logger.info(
                f"Note: Ensure Ollama's num_ctx is set to {context_window_val}. "
                f"Configure via OLLAMA_NUM_CTX environment variable or Ollama settings."
            )
            llm_new = OllamaLLM(model_name=model_name, base_url=base_url_val, context_window=context_window_val)
            
            # Initialize to resolve model name
            try:
                if not llm_new._initialized:
                    llm_new._initialize()
                # Get the resolved model name (might have :latest added)
                resolved_model = llm_new.model_name
                
                if llm_new.is_available():
                    global llm
                    llm = llm_new
                    logger.info("Ollama LLM reloaded successfully")
                    # Update config with resolved name if it changed
                    if resolved_model != model_name:
                        set_llm_config(resolved_model, base_url_val, context_window_val)
                    return {
                        "status": "success",
                        "model": resolved_model,
                        "base_url": base_url_val,
                        "context_window": context_window_val,
                        "available": True,
                        "note": f"Ensure Ollama's num_ctx is set to {context_window_val}. Configure via OLLAMA_NUM_CTX environment variable or Ollama settings."
                    }
                else:
                    logger.warning("Ollama connection failed after reload")
                    return {
                        "status": "warning",
                        "model": resolved_model,
                        "base_url": base_url_val,
                        "context_window": context_window_val,
                        "available": False,
                        "message": "Ollama not responding. Make sure Ollama is running: ollama serve"
                    }
            except Exception as e:
                logger.exception(f"Failed to initialize LLM: {e}")
                return {
                    "status": "error",
                    "model": model_name,
                    "base_url": base_url_val,
                    "context_window": context_window_val,
                    "available": False,
                    "message": f"Failed to initialize: {str(e)}"
                }
        else:
            return {"status": "error", "message": "LLM not available (httpx not installed)"}
    except Exception as e:
        logger.exception(f"Failed to update LLM config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update LLM config: {str(e)}"
        )


@app.get("/config/llm")
async def get_llm_config_endpoint() -> dict[str, Any]:
    """Get current LLM configuration."""
    config = get_llm_config()
    available = False
    llm_context_window = config.get("context_window", 4096)
    recommendation = None
    
    if llm is not None:
        try:
            available = llm.is_available()
            llm_context_window = getattr(llm, "context_window", llm_context_window)
        except Exception:
            pass
    
    # Generate recommendation based on codebase size
    if db is not None:
        try:
            # Get total document count as proxy for codebase size
            all_docs = db.list_documents()
            doc_count = len(all_docs)
            
            # Estimate lines of code (rough: ~50 lines per document chunk)
            estimated_loc = doc_count * 50
            
            # Recommend context window based on codebase size
            if estimated_loc < 10000:
                recommendation = {"size": 4096, "reason": "Small codebase (<10k LOC)"}
            elif estimated_loc < 100000:
                recommendation = {"size": 16384, "reason": "Medium codebase (10k-100k LOC)"}
            elif estimated_loc < 500000:
                recommendation = {"size": 65536, "reason": "Large codebase (100k-500k LOC)"}
            else:
                recommendation = {"size": 262144, "reason": "Very large codebase (500k+ LOC)"}
        except Exception:
            pass
    
    # Get detected context window from LLM if available
    detected_context_window = None
    memory_estimate_gb = None
    if llm is not None:
        try:
            detected_context_window = getattr(llm, "detected_context_window", None)
            # Estimate memory usage (rough: ~0.5-1 GB per 1k tokens for context)
            memory_estimate_gb = round(llm_context_window / 1000 * 0.75, 1)  # Conservative estimate
        except Exception:
            pass
    
    response = {
        "model": config["model"],
        "base_url": config["base_url"],
        "context_window": llm_context_window,
        "detected_context_window": detected_context_window,
        "memory_estimate_gb": memory_estimate_gb,
        "available": available,
        "note": f"Ensure Ollama's num_ctx is set to {llm_context_window}. "
               f"Valid options: 4096, 8192, 16384, 32768, 65536, 131072, 262144. "
               f"Configure via OLLAMA_NUM_CTX environment variable or Ollama settings.",
    }
    
    if recommendation:
        response["recommendation"] = recommendation
    
    # Add smart recommendation based on usage history
    try:
        smart_rec = get_smart_recommendation()
        if smart_rec:
            response["smart_recommendation"] = smart_rec
    except Exception:
        pass  # Don't fail if smart recommendation fails
    
    # Add mismatch warning if detected
    if detected_context_window and detected_context_window != llm_context_window:
        response["warning"] = (
            f"Context window mismatch detected! "
            f"Codexa: {llm_context_window}, Ollama: {detected_context_window}. "
            f"Update Codexa config or set OLLAMA_NUM_CTX={llm_context_window}"
        )
    
    return response


@app.get("/config/llm/models")
async def get_available_models() -> dict[str, Any]:
    """Get list of available Ollama models."""
    try:
        if not LLM_AVAILABLE:
            return {"models": [], "error": "LLM not available (httpx not installed)"}
        
        llm_config = get_llm_config()
        base_url = llm_config["base_url"]
        
        import httpx
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            resp = client.get("/api/tags")
            if resp.status_code == 200:
                models_data = resp.json().get("models", [])
                models = []
                for m in models_data:
                    name = m.get("name", "")
                    size = m.get("size", 0)
                    size_gb = size / (1024**3) if size else 0
                    models.append({
                        "name": name,
                        "size_gb": round(size_gb, 2),
                    })
                return {"models": models, "base_url": base_url}
            else:
                return {"models": [], "error": f"Ollama API error: {resp.status_code}"}
    except Exception as e:
        logger.exception(f"Failed to get available models: {e}")
        return {"models": [], "error": str(e)}


@app.post("/config/llm/test", dependencies=[Depends(verify_api_key)])
async def test_context_window(request: LLMConfigRequest) -> dict[str, Any]:
    """
    Test context window configuration by making a test query.
    
    Args:
        request: LLM configuration to test
        
    Returns:
        Test results with validation info
    """
    if not LLM_AVAILABLE:
        return {"status": "error", "message": "LLM not available (httpx not installed)"}
    
    try:
        # Get config
        current_config = get_llm_config()
        model_name = request.model or current_config["model"]
        base_url = request.base_url or current_config["base_url"]
        context_window = request.context_window or current_config.get("context_window", 4096)
        
        # Create temporary LLM instance for testing
        test_llm = OllamaLLM(model_name=model_name, base_url=base_url, context_window=context_window)
        
        try:
            test_llm._initialize()
            
            # Test with a small query
            test_context = [
                {
                    "content": "This is a test document for context window validation.",
                    "file_path": "test.py",
                    "score": 0.9,
                    "file_type": "py",
                }
            ]
            
            answer, stats = test_llm.generate_answer(
                query="Test query",
                context=test_context,
            )
            
            return {
                "status": "success",
                "model": model_name,
                "context_window": context_window,
                "detected_context_window": test_llm.detected_context_window,
                "test_stats": stats,
                "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer,
                "validated": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "model": model_name,
                "context_window": context_window,
                "message": f"Test failed: {str(e)}",
                "validated": False,
            }
    except Exception as e:
        logger.exception(f"Failed to test context window: {e}")
        return {
            "status": "error",
            "message": f"Failed to test context window: {str(e)}",
        }


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_document(document_id: str) -> None:
    """
    Delete a document by its ID.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    try:
        db.delete_document(document_id)
    except Exception as e:
        logger.exception("Failed to delete document", extra={"document_id": document_id})
        # Surface as 404 if Chroma can't find it; otherwise generic error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )


@app.delete("/documents/file", response_model=DeleteResponse, dependencies=[Depends(verify_api_key)])
async def delete_by_file(request: DeleteFileRequest) -> DeleteResponse:
    """
    Delete all documents matching a file path.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    try:
        abs_file_path = os.path.abspath(request.file_path)
        deleted_count = db.delete_by_file_path(abs_file_path)
        return DeleteResponse(
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} document(s) for file: {abs_file_path}",
        )
    except Exception as e:
        logger.exception("Failed to delete by file path", extra={"file_path": request.file_path})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete documents: {str(e)}",
        )


@app.delete("/documents/directory", response_model=DeleteResponse, dependencies=[Depends(verify_api_key)])
async def delete_by_directory(request: DeleteDirectoryRequest) -> DeleteResponse:
    """
    Delete all documents in a directory (optionally recursive).
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    try:
        abs_directory_path = os.path.abspath(request.directory_path)
        
        # Check if directory exists
        if not os.path.isdir(abs_directory_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Directory not found: {abs_directory_path}",
            )
        
        deleted_count = db.delete_by_directory(abs_directory_path, recursive=request.recursive)
        recursive_text = "recursively" if request.recursive else "non-recursively"
        return DeleteResponse(
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} document(s) {recursive_text} from directory: {abs_directory_path}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete by directory", extra={"directory_path": request.directory_path})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete documents: {str(e)}",
        )


@app.get("/documents", dependencies=[Depends(verify_api_key)])
async def list_documents(project: Optional[str] = None) -> dict[str, Any]:
    """
    List all indexed documents with metadata.

    Args:
        project: Optional project filter

    Returns:
        List of documents with metadata including indexed_at timestamp
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    # Use current project if not specified
    if project is None:
        project = get_current_project()

    try:
        documents = db.list_documents(project=project)
        
        # Enrich with file modification time and change status
        import os
        from datetime import datetime
        
        enriched_docs = []
        for doc in documents:
            file_path = doc.get("file_path", "")
            metadata = doc.get("metadata", {})
            indexed_at_str = metadata.get("indexed_at", "")
            
            # Check if file exists and get modification time
            file_exists = os.path.exists(file_path) if file_path and not file_path.startswith("http") else False
            file_modified = None
            has_changed = False
            
            if file_exists:
                try:
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if indexed_at_str:
                        indexed_at = datetime.fromisoformat(indexed_at_str)
                        has_changed = file_modified > indexed_at
                except (ValueError, OSError):
                    pass
            
            enriched_docs.append({
                "id": doc["id"],
                "file_path": file_path,
                "file_name": metadata.get("file_name", os.path.basename(file_path) if file_path else ""),
                "file_type": metadata.get("file_type", ""),
                "project": metadata.get("project", ""),
                "indexed_at": indexed_at_str,
                "file_modified": file_modified.isoformat() if file_modified else None,
                "has_changed": has_changed,
                "file_exists": file_exists,
                "metadata": metadata,
            })
        
        return {
            "documents": enriched_docs,
            "total": len(enriched_docs),
            "project": project,
        }
    except Exception as e:
        logger.exception(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@app.post("/reindex", response_model=IndexResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def reindex_documents(request: IndexRequest) -> IndexResponse:
    """
    Reindex one or more documents. This will parse and index content anew, creating new IDs.
    """
    return await index_documents(request)
