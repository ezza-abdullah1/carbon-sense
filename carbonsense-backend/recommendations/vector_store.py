"""
ChromaDB vector store abstraction for policy document storage and retrieval.
"""

import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings


class VectorStore:
    """Wraps ChromaDB operations for policy document chunks."""

    _instance = None
    _client = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
        return self._client

    def _get_embedding_function(self):
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )

    def get_collection(self):
        """Get or create the policy_documents collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name="policy_documents",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self._get_embedding_function(),
            )
        return self._collection

    def add_chunks(self, chunk_ids, documents, metadatas):
        """Add document chunks to the collection.

        Args:
            chunk_ids: List of unique IDs for each chunk.
            documents: List of text chunks.
            metadatas: List of metadata dicts per chunk.
        """
        collection = self.get_collection()
        # ChromaDB has a batch size limit, process in batches of 100
        batch_size = 100
        for i in range(0, len(chunk_ids), batch_size):
            end = min(i + batch_size, len(chunk_ids))
            collection.add(
                ids=chunk_ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

    def query(self, query_text, n_results=20, where=None, where_document=None):
        """Query the collection for similar documents.

        Args:
            query_text: The search query string.
            n_results: Number of results to return.
            where: Optional metadata filter dict.
            where_document: Optional document content filter.

        Returns:
            ChromaDB query result with ids, documents, metadatas, distances.
        """
        collection = self.get_collection()
        kwargs = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        return collection.query(**kwargs)

    def delete_by_document_id(self, document_id):
        """Delete all chunks belonging to a specific document.

        Args:
            document_id: The UUID string of the PolicyDocument.
        """
        collection = self.get_collection()
        # Get all chunk IDs for this document
        results = collection.get(
            where={"document_id": str(document_id)},
        )
        if results and results['ids']:
            collection.delete(ids=results['ids'])
        return len(results['ids']) if results and results['ids'] else 0

    def delete_all(self):
        """Delete the entire collection and recreate it."""
        client = self._get_client()
        try:
            client.delete_collection("policy_documents")
        except Exception:
            pass
        self._collection = None
        return self.get_collection()

    def count(self):
        """Return the total number of chunks in the collection."""
        collection = self.get_collection()
        return collection.count()

    def get_stats(self):
        """Return stats about the vector store."""
        collection = self.get_collection()
        total = collection.count()
        return {
            "total_chunks": total,
            "collection_name": "policy_documents",
            "embedding_model": settings.EMBEDDING_MODEL,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
        }
