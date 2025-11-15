"""
Vector Database Service using Qdrant
Stores all context as embeddings for semantic search
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

logger = logging.getLogger(__name__)


class VectorDBService:
    """
    Manages all context storage in vector database

    Everything is stored as embeddings:
    - Standup messages
    - Task descriptions
    - Help requests
    - Code discussions
    - Any team context
    """

    def __init__(self, qdrant_url: str, collection_name: str = "mcp_context"):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.client = None

    async def initialize(self):
        """Initialize connection to Qdrant"""
        try:
            self.client = QdrantClient(url=self.qdrant_url)

            # Create collection if it doesn't exist
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Gemini embedding dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise

    async def close(self):
        """Close connection"""
        if self.client:
            self.client.close()

    async def health_check(self) -> str:
        """Check Qdrant health"""
        try:
            info = self.client.get_collections()
            return f"healthy ({len(info.collections)} collections)"
        except Exception as e:
            return f"unhealthy: {str(e)}"

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Gemini's embedding model

        Uses Google's embedding-001 model (768 dimensions)
        """
        try:
            import google.generativeai as genai

            # Use Gemini embedding model
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )

            embedding = result['embedding']

            # Ensure correct dimension
            if len(embedding) != 768:
                logger.warning(f"Unexpected embedding dimension: {len(embedding)}, expected 768")

            return embedding

        except Exception as e:
            logger.error(f"Error generating Gemini embedding: {e}")

            # Fallback: Simple hash-based embedding (for development only)
            logger.warning("Falling back to hash-based embedding")
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()

            embedding = []
            for i in range(768):
                byte_val = hash_bytes[i % len(hash_bytes)]
                embedding.append((byte_val / 255.0) - 0.5)

            return embedding

    async def add_standup(
        self,
        user_id: str,
        text: str,
        parsed_data: Dict,
        timestamp: datetime
    ) -> str:
        """Add standup to vector DB"""

        point_id = f"standup_{user_id}_{timestamp.isoformat()}"

        embedding = self._generate_embedding(text)

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "type": "standup",
                "user_id": user_id,
                "text": text,
                "timestamp": timestamp.isoformat(),
                "parsed_data": parsed_data,
                "tasks_completed": parsed_data.get("tasks_completed", []),
                "blockers": parsed_data.get("blockers", []),
                "help_requests": parsed_data.get("help_requests", []),
                "sentiment": parsed_data.get("sentiment", "neutral")
            }
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

        logger.info(f"Added standup to vector DB: {point_id}")
        return point_id

    async def add_context(self, context_data: Dict) -> str:
        """
        Generic method to add any context

        This is the protocol interface - any system can add context
        """
        context_type = context_data.get("type", "general")
        timestamp = datetime.utcnow()
        text = context_data.get("text", str(context_data))

        point_id = f"{context_type}_{timestamp.isoformat()}"
        embedding = self._generate_embedding(text)

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                **context_data,
                "timestamp": timestamp.isoformat()
            }
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

        return point_id

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across all context

        This is the power of MCP - find anything by meaning, not just keywords
        """
        query_embedding = self._generate_embedding(query)

        search_filter = None
        if filter_type:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="type",
                        match=MatchValue(value=filter_type)
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=search_filter
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "text": r.payload.get("text", ""),
                "type": r.payload.get("type", ""),
                "user_id": r.payload.get("user_id", ""),
                "payload": r.payload
            }
            for r in results
        ]

    async def find_experts(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find team members with expertise in a topic

        Searches past standups and tasks for who has worked on similar things
        """
        # Search for context related to topic
        results = await self.semantic_search(topic, limit=20)

        # Aggregate by user
        user_scores = {}
        for result in results:
            user_id = result.get("user_id")
            if user_id:
                user_scores[user_id] = user_scores.get(user_id, 0) + result["score"]

        # Sort by score
        experts = [
            {"user_id": user_id, "score": score}
            for user_id, score in sorted(
                user_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

        return experts[:limit]

    async def get_user_context(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get all context for a user in the last N days"""

        # TODO: Add date filtering
        # For now, filter by user_id

        search_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )

        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=search_filter,
            limit=100
        )

        return [
            {
                "id": r.id,
                "text": r.payload.get("text", ""),
                "type": r.payload.get("type", ""),
                "timestamp": r.payload.get("timestamp", ""),
                "payload": r.payload
            }
            for r in results[0]  # scroll returns (points, next_offset)
        ]
