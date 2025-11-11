"""Vector database layer using ChromaDB for semantic search."""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid


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
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

        # Initialize embedding model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

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
        return embedding.tolist()

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

        # Add file_path to metadata
        full_metadata = {**metadata, "file_path": file_path}

        # Convert non-string metadata values to strings for ChromaDB
        serialized_metadata = {}
        for key, value in full_metadata.items():
            if isinstance(value, (list, dict)):
                serialized_metadata[key] = str(value)
            else:
                serialized_metadata[key] = str(value)

        # Index the document
        self.collection.add(
            documents=[content],
            metadatas=[serialized_metadata],
            ids=[doc_id],
        )

        return doc_id

    def index_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Index multiple documents.

        Args:
            documents: List of document dictionaries with content, file_path, and metadata

        Returns:
            List of document IDs
        """
        doc_ids = []
        for doc in documents:
            doc_id = self.index_document(
                content=doc["content"],
                file_path=doc["file_path"],
                metadata=doc.get("metadata", {}),
            )
            doc_ids.append(doc_id)
        return doc_ids

    def search(
        self, query: str, top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None
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
        # Perform search
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_metadata,
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for idx, doc_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "document_id": doc_id,
                        "content": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                        "score": (
                            1.0 - results["distances"][0][idx] if results["distances"] else 0.0
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

    def clear_all(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(name=self.collection.name)
        self.collection = self.client.get_or_create_collection(name=self.collection.name)
