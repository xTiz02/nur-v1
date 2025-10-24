import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
import json
import ollama
from contextlib import contextmanager


class PgVectorRepository:
    """
    Repository class for interacting with pgvector database.
    Handles vector storage, search, and retrieval operations.
    """

    def __init__(
        self,
        database: str,
        user: str,
        password: str,
        host: str = "localhost",
        port: str = "5432",
        table_name: str = "py_vector_store",
        embedding_model: str = "nomic-embed-text",
        embedding_dimension: int = 768
    ):
        """
        Initialize the PgVector repository.

        Args:
            database: Database name
            user: Database user
            password: Database password
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            table_name: Name of the vector store table
            embedding_model: Ollama model for embeddings
            embedding_dimension: Dimension of embedding vectors
        """
        self.db_config = {
            "database": database,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.table_name = table_name
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = True
        try:
            yield conn
        finally:
            conn.close()

    def initialize_database(self) -> None:
        """Initialize database with required extensions and table."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE EXTENSION IF NOT EXISTS vector;
                    CREATE EXTENSION IF NOT EXISTS hstore;
                    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
                        content text,
                        metadata json,
                        embedding vector({dimension})
                    );

                    CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
                    ON {table_name} USING HNSW (embedding vector_cosine_ops);
                """.format(table_name=self.table_name,
                           dimension=self.embedding_dimension))

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for given text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        response = ollama.embeddings(model=self.embedding_model, prompt=text)
        return response["embedding"]

    def insert_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Insert a single document into the vector store.

        Args:
            content: Document content
            metadata: Optional metadata dictionary
            embedding: Optional pre-computed embedding (if None, will be generated)

        Returns:
            UUID of inserted document
        """
        if embedding is None:
            embedding = self.generate_embedding(content)

        if metadata is None:
            metadata = {}

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table_name} (content, metadata, embedding) 
                    VALUES (%s, %s, %s) RETURNING id
                    """,
                    (content, json.dumps(metadata), embedding)
                )
                doc_id = cur.fetchone()[0]
                return str(doc_id)

    def insert_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert multiple documents in batch.

        Args:
            documents: List of dicts with 'content', optional 'metadata' and 'embedding'

        Returns:
            List of UUIDs for inserted documents
        """
        inserted_ids = []

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for doc in documents:
                    content = doc.get("content")
                    metadata = doc.get("metadata", {})
                    embedding = doc.get("embedding")

                    if embedding is None:
                        embedding = self.generate_embedding(content)

                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name} (content, metadata, embedding) 
                        VALUES (%s, %s, %s) RETURNING id
                        """,
                        (content, json.dumps(metadata), embedding)
                    )
                    doc_id = cur.fetchone()[0]
                    inserted_ids.append(str(doc_id))

        return inserted_ids

    def search_by_vector(
        self,
        query: str,
        limit: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Optional similarity threshold (0-1)

        Returns:
            List of matching documents with content, metadata, and distance
        """
        query_embedding = self.generate_embedding(query)

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if threshold is not None:
                    cur.execute(
                        f"""
                        SELECT id, content, metadata, 
                               1 - (embedding <=> %s::vector) as similarity
                        FROM {self.table_name}
                        WHERE 1 - (embedding <=> %s::vector) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, query_embedding, threshold,
                         query_embedding, limit)
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT id, content, metadata,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM {self.table_name}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, query_embedding, limit)
                    )

                results = cur.fetchall()
                return [dict(row) for row in results]

    def search_by_tokens(
        self,
        tokens: List[str],
        limit: int = 5,
        combine_method: str = "average"
    ) -> List[Dict[str, Any]]:
        """
        Search for documents matching multiple tokens.

        Args:
            tokens: List of token strings to search for
            limit: Maximum number of results
            combine_method: How to combine token embeddings ('average' or 'concat')

        Returns:
            List of matching documents
        """
        if combine_method == "average":
            # Generate embeddings for each token and average them
            embeddings = [self.generate_embedding(token) for token in tokens]
            query_embedding = [
                sum(vals) / len(vals)
                for vals in zip(*embeddings)
            ]
        else:
            # Concatenate tokens and generate single embedding
            combined_text = " ".join(tokens)
            query_embedding = self.generate_embedding(combined_text)

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, content, metadata,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM {self.table_name}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, limit)
                )

                results = cur.fetchall()
                return [dict(row) for row in results]

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its UUID.

        Args:
            doc_id: Document UUID

        Returns:
            Document dictionary or None if not found
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, content, metadata
                    FROM {self.table_name}
                    WHERE id = %s
                    """,
                    (doc_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by its UUID.

        Args:
            doc_id: Document UUID

        Returns:
            True if deleted, False if not found
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.table_name} WHERE id = %s",
                    (doc_id,)
                )
                return cur.rowcount > 0

    def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a document's content and/or metadata.
        If content is updated, embedding is regenerated.

        Args:
            doc_id: Document UUID
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if not found
        """
        updates = []
        params = []

        if content is not None:
            embedding = self.generate_embedding(content)
            updates.extend(["content = %s", "embedding = %s"])
            params.extend([content, embedding])

        if metadata is not None:
            updates.append("metadata = %s")
            params.append(json.dumps(metadata))

        if not updates:
            return False

        params.append(doc_id)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {self.table_name}
                    SET {', '.join(updates)}
                    WHERE id = %s
                    """,
                    params
                )
                return cur.rowcount > 0

    def count_documents(self) -> int:
        """Get total number of documents in the store."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                return cur.fetchone()[0]

    def clear_all(self) -> None:
        """Delete all documents from the store."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name}")


# Example usage
if __name__ == "__main__":
    # Initialize repository
    repo = PgVectorRepository(
        database="vector",
        user="user",
        password="pass",
        host="localhost",
        port="5432"
    )

    # Initialize database
    repo.initialize_database()

    # Insert documents
    documents = [
        {
            "content": "Llamas are members of the camelid family",
            "metadata": {"category": "biology", "index": 0}
        },
        {
            "content": "Llamas were first domesticated 4,000 to 5,000 years ago",
            "metadata": {"category": "history", "index": 1}
        }
    ]

    ids = repo.insert_documents_batch(documents)
    print(f"Inserted documents: {ids}")

    # Search by query
    results = repo.search_by_vector("Tell me about llamas", limit=3)
    print("\nSearch results:")
    for result in results:
        print(
            f"- {result['content'][:50]}... (similarity: {result['similarity']:.3f})")

    # Search by tokens
    token_results = repo.search_by_tokens(["llamas", "domesticated"], limit=2)
    print("\nToken search results:")
    for result in token_results:
        print(f"- {result['content'][:50]}...")

    # Get document count
    print(f"\nTotal documents: {repo.count_documents()}")