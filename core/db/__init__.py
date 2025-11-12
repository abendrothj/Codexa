"""Vector database layer using ChromaDB for semantic search."""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VectorDatabase:
    """ChromaDB-based vector database for semantic search."""

    def __init__(
        self, persist_directory: str = "./chroma_data", collection_name: str = "codexa"
    ) -> None:
        """
        Initialize the vector database.

        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
        """
        # Use PersistentClient to ensure data persists across restarts
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
            )
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

        # Initialize embedding model
        model_name = os.getenv("CODEXA_MODEL_NAME", "all-MiniLM-L6-v2")
        model_cache = os.getenv("CODEXA_MODEL_CACHE", None)
        offline = os.getenv("CODEXA_OFFLINE", "false").lower() == "true"
        
        # Build kwargs for SentenceTransformer
        model_kwargs: Dict[str, Any] = {}
        if model_cache:
            model_kwargs["cache_folder"] = model_cache
        # local_files_only is only supported in newer versions
        # For older versions, we'll handle offline mode differently
        try:
            import inspect
            sig = inspect.signature(SentenceTransformer.__init__)
            if "local_files_only" in sig.parameters:
                model_kwargs["local_files_only"] = offline
        except Exception:
            pass  # If inspection fails, just skip the parameter
        
        self.embedding_model = SentenceTransformer(model_name, **model_kwargs)

    def _generate_id(self) -> str:
        """Generate a unique document ID."""
        return str(uuid.uuid4())

    def _create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_tensor=False)
        # SentenceTransformers may return numpy array; ensure list[float]
        try:
            return embedding.tolist()  # type: ignore[attr-defined]
        except AttributeError:
            return list(map(float, embedding))  # fallback if already list

    def index_document(self, content: str, file_path: str, metadata: Dict[str, Any]) -> str:
        """
        Index a document in the vector database.

        Args:
            content: Document content
            file_path: Path to the file
            metadata: Additional metadata

        Returns:
            Document ID
        """
        doc_id = self._generate_id()

        # Add file_path and indexed_at timestamp to metadata
        indexed_at = datetime.now().isoformat()
        full_metadata = {**metadata, "file_path": file_path, "indexed_at": indexed_at}

        # Convert non-string metadata values to strings for ChromaDB
        serialized_metadata = {}
        for key, value in full_metadata.items():
            if isinstance(value, (list, dict)):
                serialized_metadata[key] = str(value)
            else:
                serialized_metadata[key] = str(value)

        # Create embedding once for the document
        embedding_vector = self._create_embedding(content)

        # Index the document
        self.collection.add(
            documents=[content],
            metadatas=[serialized_metadata],
            ids=[doc_id],
            embeddings=[embedding_vector],
        )

        return doc_id

    def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> List[str]:
        """
        Index multiple documents efficiently using batch operations.

        Args:
            documents: List of document dictionaries with content, file_path, and metadata
            batch_size: Number of documents to process in each batch (for embeddings and DB writes)

        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        doc_ids = []
        from datetime import datetime
        
        # Process in batches for better performance
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start:batch_start + batch_size]
            
            # Prepare batch data
            batch_contents = []
            batch_metadatas = []
            batch_ids = []
            
            for doc in batch:
                doc_id = self._generate_id()
                batch_ids.append(doc_id)
                
                # Prepare metadata
                indexed_at = datetime.now().isoformat()
                full_metadata = {
                    **doc.get("metadata", {}),
                    "file_path": doc["file_path"],
                    "indexed_at": indexed_at,
                }
                
                # Serialize metadata
                serialized_metadata = {}
                for key, value in full_metadata.items():
                    if isinstance(value, (list, dict)):
                        serialized_metadata[key] = str(value)
                    else:
                        serialized_metadata[key] = str(value)
                
                batch_contents.append(doc["content"])
                batch_metadatas.append(serialized_metadata)
            
            # Batch create embeddings (much faster than individual calls)
            try:
                batch_embeddings = self.embedding_model.encode(
                    batch_contents,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    batch_size=min(batch_size, 32),  # SentenceTransformers batch size
                )
                # Convert to list format
                batch_embeddings_list = []
                for emb in batch_embeddings:
                    try:
                        batch_embeddings_list.append(emb.tolist())
                    except AttributeError:
                        batch_embeddings_list.append(list(map(float, emb)))
            except Exception as e:
                # Fallback to individual embeddings if batch fails
                logger.warning(f"Batch embedding failed, using individual embeddings: {e}")
                batch_embeddings_list = [self._create_embedding(content) for content in batch_contents]
            
            # Batch add to ChromaDB (much faster than individual adds)
            try:
                self.collection.add(
                    documents=batch_contents,
                    metadatas=batch_metadatas,
                    ids=batch_ids,
                    embeddings=batch_embeddings_list,
                )
                doc_ids.extend(batch_ids)
            except Exception as e:
                # Fallback to individual adds if batch fails
                logger.warning(f"Batch add failed, using individual adds: {e}")
                for i, doc in enumerate(batch):
                    try:
                        doc_id = self.index_document(
                            content=doc["content"],
                            file_path=doc["file_path"],
                            metadata=doc.get("metadata", {}),
                        )
                        doc_ids.append(doc_id)
                    except Exception as e2:
                        logger.exception(f"Failed to index document: {e2}")
        
        return doc_ids

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with content, metadata, and scores
        """
        # Compute query embedding and perform search
        query_embedding = self._create_embedding(query)
        fetch = max(top_k + offset, 0) or top_k
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch,
            where=filter_metadata,
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            dists = results.get("distances", [[None] * len(ids)])[0]
            # Apply offset slice
            start = min(offset, len(ids))
            end = min(offset + top_k, len(ids)) if top_k > 0 else len(ids)
            for idx in range(start, end):
                doc_id = ids[idx]
                formatted_results.append(
                    {
                        "document_id": doc_id,
                        "content": docs[idx],
                        "metadata": metas[idx] if metas else {},
                        "score": (
                            1.0 - dists[idx] if dists and dists[idx] is not None else 0.0
                        ),
                    }
                )

        return formatted_results

    def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the database.

        Args:
            doc_id: Document ID to delete
        """
        self.collection.delete(ids=[doc_id])
    
    def delete_by_file_path(self, file_path: str) -> int:
        """
        Delete all documents matching a file path.

        Args:
            file_path: Absolute file path to match

        Returns:
            Number of documents deleted
        """
        # Get all documents and filter by file_path
        results = self.collection.get(limit=10000)
        ids_to_delete = []
        
        if results["ids"] and results["metadatas"]:
            for idx, metadata in enumerate(results["metadatas"]):
                if metadata.get("file_path") == file_path:
                    ids_to_delete.append(results["ids"][idx])
        
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        
        return len(ids_to_delete)
    
    def delete_by_directory(self, directory_path: str, recursive: bool = True) -> int:
        """
        Delete all documents in a directory (optionally recursive).

        Args:
            directory_path: Absolute directory path
            recursive: Whether to delete files in subdirectories

        Returns:
            Number of documents deleted
        """
        import os
        from pathlib import Path
        
        dir_path = Path(directory_path).resolve()
        ids_to_delete = []
        
        # Get all documents
        results = self.collection.get(limit=10000)
        
        if results["ids"] and results["metadatas"]:
            for idx, metadata in enumerate(results["metadatas"]):
                file_path_str = metadata.get("file_path", "")
                if not file_path_str:
                    continue
                
                file_path = Path(file_path_str)
                try:
                    # Check if file is in the directory
                    if recursive:
                        # Check if file_path is within directory_path
                        try:
                            file_path.resolve().relative_to(dir_path)
                            ids_to_delete.append(results["ids"][idx])
                        except ValueError:
                            # File is not within directory
                            pass
                    else:
                        # Only direct children
                        if file_path.parent.resolve() == dir_path:
                            ids_to_delete.append(results["ids"][idx])
                except (OSError, ValueError):
                    # Path resolution failed, skip
                    continue
        
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        
        return len(ids_to_delete)

    def list_documents(
        self,
        project: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        List all indexed documents with their metadata.

        Args:
            project: Optional project filter
            limit: Maximum number of documents to return

        Returns:
            List of documents with id, metadata, and file_path
        """
        filter_metadata = {}
        if project:
            filter_metadata["project"] = project

        # Get all documents from the collection
        results = self.collection.get(
            limit=limit,
            where=filter_metadata if filter_metadata else None,
        )

        documents = []
        ids = results["ids"]
        metadatas = results["metadatas"] if results["metadatas"] else [{}] * len(ids)

        for idx, doc_id in enumerate(ids):
            metadata = metadatas[idx] if metadatas else {}
            documents.append({
                "id": doc_id,
                "file_path": metadata.get("file_path", ""),
                "metadata": metadata,
            })

        return documents

    def clear_all(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(name=self.collection.name)
        self.collection = self.client.get_or_create_collection(name=self.collection.name)
