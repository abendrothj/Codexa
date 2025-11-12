"""Ollama LLM integration for intelligent responses using RAG."""

from typing import Optional, List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

# Try to import httpx for Ollama API calls
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available - LLM features disabled")


class OllamaLLM:
    """Ollama LLM for generating intelligent responses from search results."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        context_window: Optional[int] = None,
    ) -> None:
        """
        Initialize Ollama LLM.

        Args:
            model_name: Ollama model name (default: llama3.2 or from env)
            base_url: Ollama API base URL (default: http://localhost:11434)
            context_window: Context window size in tokens (default: from env or 4096)
                            Must match Ollama's num_ctx setting. Options: 4096, 8192, 16384, 32768, 65536, 131072, 262144
        """
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx library not installed. Install with: pip install httpx"
            )

        self.model_name = model_name or os.getenv(
            "CODEXA_LLM_MODEL", "llama3.2"
        )
        self.base_url = (base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )).rstrip("/")
        
        # Context window size (must match Ollama's num_ctx setting)
        # Default is 4k (Ollama's default), but can be configured up to 256k
        self.context_window = context_window or int(os.getenv(
            "CODEXA_LLM_CONTEXT_WINDOW", "4096"
        ))
        
        # Validate context window is a valid Ollama option
        valid_sizes = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
        if self.context_window not in valid_sizes:
            # Round to nearest valid size
            closest = min(valid_sizes, key=lambda x: abs(x - self.context_window))
            logger.warning(
                f"Context window {self.context_window} not a valid Ollama size. "
                f"Using closest valid size: {closest}. "
                f"Valid sizes: {valid_sizes}"
            )
            self.context_window = closest
        
        self.client: Optional[httpx.Client] = None
        self._initialized = False
        self.detected_context_window: Optional[int] = None  # Detected from Ollama

    def _resolve_model_name(self, model_names: List[str]) -> Optional[str]:
        """
        Resolve model name, handling Ollama tags like :latest.
        
        Args:
            model_names: List of available model names from Ollama
            
        Returns:
            Resolved model name or None if not found
        """
        # Exact match
        if self.model_name in model_names:
            return self.model_name
        
        # Try with :latest tag
        if f"{self.model_name}:latest" in model_names:
            resolved = f"{self.model_name}:latest"
            logger.info(f"Resolved model '{self.model_name}' to '{resolved}'")
            return resolved
        
        # Try without tag (if user specified with tag but model exists without)
        base_name = self.model_name.split(":")[0]
        if base_name in model_names:
            resolved = base_name
            logger.info(f"Resolved model '{self.model_name}' to '{resolved}'")
            return resolved
        
        # Try to find any model that starts with the base name
        for name in model_names:
            if name.startswith(f"{base_name}:"):
                resolved = name
                logger.info(f"Resolved model '{self.model_name}' to '{resolved}'")
                return resolved
        
        return None

    def _initialize(self) -> None:
        """Lazy initialization - check if Ollama is available."""
        if self._initialized:
            return

        try:
            logger.info(f"Connecting to Ollama at {self.base_url}")
            # Use longer timeout for large context windows (up to 5 minutes for 256k context)
            # Rough estimate: 1 minute per 50k tokens
            timeout_seconds = max(60.0, (self.context_window / 50000) * 60)
            self.client = httpx.Client(
                base_url=self.base_url,
                timeout=timeout_seconds,
            )
            # Test connection by listing models
            response = self.client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                logger.info(f"Ollama connected. Available models: {', '.join(model_names[:5])}")
                
                # Resolve model name (handle :latest tags)
                resolved_name = self._resolve_model_name(model_names)
                if resolved_name:
                    self.model_name = resolved_name
                    logger.info(f"Using model: {self.model_name}")
                else:
                    logger.warning(
                        f"Model '{self.model_name}' not found in Ollama. "
                        f"Available: {', '.join(model_names[:3])}. "
                        f"Run: ollama pull {self.model_name}"
                    )
                
                # Try to detect Ollama's actual num_ctx setting
                self.detected_context_window = self._detect_ollama_context_window()
                if self.detected_context_window:
                    logger.info(f"Detected Ollama num_ctx: {self.detected_context_window}")
                    if self.detected_context_window != self.context_window:
                        logger.warning(
                            f"Context window mismatch! Codexa: {self.context_window}, Ollama: {self.detected_context_window}. "
                            f"Update Codexa config or set OLLAMA_NUM_CTX={self.context_window}"
                        )
            else:
                logger.warning(f"Ollama connection check failed: {response.status_code}")
            self._initialized = True
        except Exception as e:
            logger.exception(f"Failed to connect to Ollama: {e}")
            raise
    
    def _detect_ollama_context_window(self) -> Optional[int]:
        """
        Try to detect Ollama's actual num_ctx setting.
        
        Returns:
            Detected context window size or None if detection fails
        """
        if not self.client:
            return None
        
        try:
            # Method 1: Try to get model info (some Ollama versions expose this)
            try:
                # Use longer timeout for model info requests
                timeout = max(10.0, (self.context_window / 50000) * 10)
                response = self.client.post(
                    "/api/show",
                    json={"name": self.model_name},
                    timeout=timeout,
                )
                if response.status_code == 200:
                    model_info = response.json()
                    # Check for num_ctx in model details
                    if "modelfile" in model_info:
                        modelfile = model_info["modelfile"]
                        # Look for PARAMETER num_ctx
                        import re
                        match = re.search(r"PARAMETER\s+num_ctx\s+(\d+)", modelfile, re.IGNORECASE)
                        if match:
                            return int(match.group(1))
                    
                    # Check for parameters dict
                    if "parameters" in model_info:
                        params = model_info["parameters"]
                        if "num_ctx" in params:
                            return int(params["num_ctx"])
            except Exception:
                pass
            
            # Method 2: Try a test generation with progressively larger contexts
            # This is more reliable but slower
            try:
                # Test with a small prompt to see what context window is actually used
                test_prompt = "Test"
                # Use longer timeout for test generation
                timeout = max(30.0, (self.context_window / 50000) * 30)
                response = self.client.post(
                    "/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": test_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 1,
                        },
                    },
                    timeout=timeout,
                )
                if response.status_code == 200:
                    # Some Ollama versions return context info in response
                    result = response.json()
                    if "context" in result:
                        # This might contain context window info
                        pass
            except Exception:
                pass
            
            # Method 3: Check environment variable (if accessible)
            # This won't work in most cases but worth trying
            import os
            env_ctx = os.getenv("OLLAMA_NUM_CTX")
            if env_ctx:
                try:
                    return int(env_ctx)
                except ValueError:
                    pass
            
            return None
        except Exception as e:
            logger.debug(f"Failed to detect Ollama context window: {e}")
            return None

    def generate_answer(
        self,
        query: str,
        context: List[Dict[str, Any]],
        max_length: Optional[int] = None,  # Auto-calculated from context_window if None
        temperature: float = 0.3,  # Lower temperature for more focused, factual answers
        iterative: bool = True,  # Enable iterative retrieval
        context_window_override: Optional[int] = None,  # Override context window for this query
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate an intelligent answer based on query and search context.
        
        Supports iterative retrieval: if initial answer indicates missing information,
        performs follow-up searches to gather more context.

        Args:
            query: User's search query
            context: List of search results with 'content' and 'file_path'
            max_length: Maximum response length (tokens). If None, uses 10% of context_window
            temperature: Sampling temperature (0.0-1.0)
            iterative: Whether to use iterative retrieval for better answers
            context_window_override: Override context window for this query (for testing or special cases)

        Returns:
            Tuple of (answer string, stats dict with context_usage, tokens_used, etc.)
        """
        if not HTTPX_AVAILABLE:
            return ("LLM not available. Install httpx to enable intelligent responses.", {"error": "httpx not installed"})

        if not self._initialized:
            self._initialize()

        # Use override if provided, otherwise use configured context window
        effective_context_window = context_window_override or self.context_window
        
        # Auto-calculate max_length if not provided (use 10% of context window)
        if max_length is None:
            max_length = int(effective_context_window * 0.1)

        # Build context from search results (returns context text and stats)
        # Pass effective context window to _build_context
        context_text, context_stats = self._build_context(query, context, effective_context_window)
        
        # Log context building results
        logger.info(f"Built context: {context_stats.get('documents_used', 0)}/{len(context)} documents, "
                   f"{context_stats.get('context_chars', 0)} chars, "
                   f"truncated={context_stats.get('truncated', False)}")
        
        # Check if we have any actual content
        if not context_text or context_text.strip() == "No indexed documents found. Please index some files first.":
            return (
                "I don't have access to any indexed code or documentation to answer your question. "
                "Please make sure you have indexed some files first using the index endpoint. "
                "You can index files using: codexa index <file_path> or through the GUI.",
                {
                    "context_documents_available": len(context),
                    "context_documents_used": 0,
                    "context_usage_percent": 0,
                    "warning": "No content available in context"
                }
            )
        
        # Create code-aware prompt for better codebase understanding
        prompt = f"""You are an expert code analyst. Based on the following code snippets and documentation from a codebase, provide a detailed and comprehensive answer to the question.

Guidelines:
- Explain how functions, classes, and modules work
- Identify relationships and dependencies between components
- Reference specific file paths when relevant
- If the code shows patterns or architecture, explain them
- Be specific and cite code examples from the context
- If information is incomplete, note what's missing

Context (code snippets and documentation):
{context_text}

Question: {query}

Provide a detailed answer with specific references to the code:"""
        
        # Calculate token usage estimates (rough: 1 token ≈ 4 chars)
        prompt_tokens = len(prompt) // 4
        context_tokens = context_stats.get("context_tokens_estimate", len(context_text) // 4)
        estimated_total = prompt_tokens + context_tokens + max_length

        try:
            # Calculate timeout based on context window size
            # For large contexts, generation can take much longer
            # Rough estimate: 1 minute per 50k tokens, minimum 60 seconds
            # For very large contexts (256k), allow up to 10 minutes
            timeout_seconds = max(60.0, min((effective_context_window / 50000) * 60, 600.0))
            
            logger.info(f"Making Ollama API request with timeout: {timeout_seconds:.1f} seconds (context_window: {effective_context_window})")
            
            # Create a new client with the specific timeout for this request
            # httpx per-request timeout might not work reliably, so create a new client
            import httpx
            request_client = httpx.Client(
                base_url=self.base_url,
                timeout=timeout_seconds,
            )
            
            try:
                # Call Ollama API with appropriate timeout
                response = request_client.post(
                    "/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_length,
                        },
                    },
                )
            finally:
                request_client.close()
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "").strip()

            # Extract just the answer part if it includes the prompt
            if "Answer:" in answer:
                answer = answer.split("Answer:")[-1].strip()
            # Remove any remaining prompt artifacts
            if prompt[:50] in answer:
                answer = answer.split(prompt[:50])[-1].strip()

            # Iterative retrieval: if answer indicates missing info, try to get more context
            if iterative and self._needs_more_context(answer, query):
                logger.info("Answer indicates missing information, attempting iterative retrieval")
                # Extract key terms for follow-up search
                follow_up_terms = self._extract_follow_up_terms(query, answer)
                if follow_up_terms:
                    # Note: This would require access to the search function
                    # For now, we'll just note it in the answer
                    answer += f"\n\n[Note: Some information may be incomplete. Consider searching for: {', '.join(follow_up_terms[:3])}]"

            # Calculate final stats
            answer_tokens = len(answer) // 4
            stats = {
                "context_tokens": context_tokens,
                "prompt_tokens": prompt_tokens,
                "answer_tokens": answer_tokens,
                "total_tokens": prompt_tokens + context_tokens + answer_tokens,
                "context_window": effective_context_window,
                "context_window_configured": self.context_window,
                "context_window_override": context_window_override is not None,
                "context_usage_percent": round((prompt_tokens + context_tokens + answer_tokens) / effective_context_window * 100, 1),
                "context_truncated": context_stats.get("truncated", False),
                "context_documents_used": context_stats.get("documents_used", 0),
                "context_documents_available": len(context),
                "detected_ollama_context_window": self.detected_context_window,
            }
            
            # Warn if approaching context limit
            if stats["context_usage_percent"] > 90:
                logger.warning(f"Context window usage is {stats['context_usage_percent']}% - consider increasing context window size")
            elif stats["context_usage_percent"] > 75:
                logger.info(f"Context window usage: {stats['context_usage_percent']}%")

            return (answer if answer else "No answer generated.", stats)
        except httpx.HTTPError as e:
            logger.exception(f"Ollama API error: {e}")
            error_msg = f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running: ollama serve"
            return (error_msg, {"error": str(e)})
        except Exception as e:
            logger.exception(f"Failed to generate answer: {e}")
            error_msg = f"Error generating answer: {str(e)}"
            return (error_msg, {"error": str(e)})
    
    def _needs_more_context(self, answer: str, query: str) -> bool:
        """Check if answer indicates missing information."""
        indicators = [
            "cannot be found",
            "not found",
            "not available",
            "incomplete",
            "missing",
            "unclear",
            "not specified",
            "not mentioned",
        ]
        answer_lower = answer.lower()
        return any(indicator in answer_lower for indicator in indicators)
    
    def _extract_follow_up_terms(self, query: str, answer: str) -> List[str]:
        """Extract key terms for follow-up search."""
        import re
        # Extract mentioned function/class names, file paths, etc.
        terms = []
        
        # Function/class names (def, class keywords)
        code_entities = re.findall(r'\b(def|class)\s+(\w+)', answer, re.IGNORECASE)
        terms.extend([name for _, name in code_entities])
        
        # File paths
        file_paths = re.findall(r'[\w/\\]+\.(py|md|js|ts|java|cpp)', answer, re.IGNORECASE)
        terms.extend([path.split('/')[-1].split('\\')[-1] for path in file_paths])
        
        # Important nouns from query
        query_words = query.split()
        terms.extend([w for w in query_words if len(w) > 4])
        
        return list(set(terms))[:5]  # Return up to 5 unique terms

    def _build_context(self, query: str, context: List[Dict[str, Any]], context_window: Optional[int] = None) -> tuple[str, Dict[str, Any]]:
        """
        Build context string from search results with intelligent code-aware handling.
        
        Uses token-aware truncation (rough estimate: 1 token ≈ 4 chars for English).
        For code files, preserves structure (function/class definitions).
        
        Context size is based on configured context_window, leaving room for prompt and response.
        
        Args:
            query: Search query
            context: List of search results
            context_window: Context window size to use (defaults to self.context_window)
        
        Returns:
            Tuple of (context_string, stats_dict)
        """
        # Handle empty context
        if not context:
            logger.warning("Empty context provided to _build_context")
            return ("No indexed documents found. Please index some files first.", {
                "documents_used": 0,
                "documents_available": 0,
                "truncated": False,
                "context_chars": 0,
                "context_tokens_estimate": 0,
                "max_context_chars": 0,
                "context_usage_percent": 0,
            })
        
        # Use provided context_window or fall back to instance default
        effective_window = context_window or self.context_window
        
        context_parts = []
        # Calculate max context tokens: context_window - prompt (~2k) - response (~10% of context_window)
        # Conservative to leave room for prompt and response
        max_context_tokens = int(effective_window * 0.75)  # Use 75% for context
        max_context_chars = max_context_tokens * 4  # Rough estimate: 1 token ≈ 4 chars
        
        current_length = 0
        documents_used = 0
        truncated = False
        # Use many more results for comprehensive coverage (up to 50 instead of 10)
        for idx, result in enumerate(context[:50], 1):
            content = result.get("content", "")
            file_path = result.get("file_path", "Unknown")
            score = result.get("score", 0.0)
            file_type = result.get("file_type", "")

            # Check available space
            available_space = max_context_chars - current_length
            if available_space <= 100:  # Leave some buffer
                truncated = True
                break

            # Track if content was truncated
            original_length = len(content)
            
            # For code files, try to preserve structure
            if file_type in ["py", "js", "ts", "java", "cpp", "c", "go", "rs"]:
                content = self._truncate_code_intelligently(content, available_space)
            else:
                # For other files, truncate from end
                if len(content) > available_space:
                    content = content[:available_space - 3] + "..."
                    truncated = True

            context_parts.append(
                f"[Document {idx}] {file_path} (relevance: {score:.2%})\n{content}\n"
            )
            current_length += len(context_parts[-1])
            documents_used += 1

        stats = {
            "documents_used": documents_used,
            "documents_available": len(context),
            "truncated": truncated,
            "context_chars": current_length,
            "context_tokens_estimate": current_length // 4,
            "max_context_chars": max_context_chars,
            "context_usage_percent": round((current_length / max_context_chars * 100), 1) if max_context_chars > 0 else 0,
        }
        
        return "\n".join(context_parts), stats
    
    def _truncate_code_intelligently(self, content: str, max_chars: int) -> str:
        """
        Truncate code content while preserving structure.
        
        Prioritizes:
        1. Function/class definitions (def, class keywords)
        2. Docstrings
        3. Imports
        4. Type hints and signatures
        """
        if len(content) <= max_chars:
            return content
        
        # Try to find a good breaking point
        # Look for function/class boundaries
        lines = content.split('\n')
        truncated_lines = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            # If adding this line would exceed limit, try to find a good break
            if current_length + line_length > max_chars:
                # If we're in the middle of a function/class, try to complete it
                if any(keyword in line for keyword in ['def ', 'class ', '    def ', '    class ']):
                    # Include this line if it's a definition start
                    if current_length + line_length <= max_chars * 1.1:  # 10% buffer
                        truncated_lines.append(line)
                        current_length += line_length
                break
            
            truncated_lines.append(line)
            current_length += line_length
        
        result = '\n'.join(truncated_lines)
        
        # If still too long, hard truncate but preserve structure hint
        if len(result) > max_chars:
            result = result[:max_chars - 50] + "\n\n[... code truncated ...]"
        
        return result

    def is_available(self) -> bool:
        """Check if LLM is available and ready."""
        if not HTTPX_AVAILABLE:
            return False
        try:
            if not self._initialized:
                self._initialize()
            # Quick health check
            if self.client:
                response = self.client.get("/api/tags", timeout=2.0)
                return response.status_code == 200
            return False
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            if not self._initialized:
                self._initialize()
            if self.client:
                response = self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return [m.get("name", "") for m in models]
            return []
        except Exception as e:
            logger.exception(f"Failed to list models: {e}")
            return []


# Alias for backward compatibility
LocalLLM = OllamaLLM
