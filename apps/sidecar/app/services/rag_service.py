"""
RAG (Retrieval Augmented Generation) Service for Sclip
Provides semantic search, vector storage, and context-aware retrieval
"""

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np
from dataclasses import dataclass, asdict
import uuid

# Vector database and embeddings
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: ChromaDB not available. Install with: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: SentenceTransformers not available. Install with: pip install sentence-transformers")

from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Document:
    """Represents a document in the RAG system"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class SearchResult:
    """Represents a search result from RAG"""
    document: Document
    similarity_score: float
    relevance_score: float

class RAGService:
    """
    RAG Service for semantic search and context-aware retrieval
    """
    
    def __init__(self, persist_directory: str = "./rag_storage"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize vector database
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name="sclip_documents",
                metadata={"description": "Sclip RAG documents"}
            )
        else:
            self.client = None
            self.collection = None
        
        # Initialize embeddings model
        if EMBEDDINGS_AVAILABLE:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.embedding_model = None
        
        # Document cache for quick access
        self.document_cache: Dict[str, Document] = {}
        
        logger.info("RAG Service initialized")
    
    async def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add a document to the RAG system"""
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Create document
            document = Document(
                id=doc_id,
                content=content,
                metadata=metadata or {}
            )
            
            # Generate embedding if model is available
            if self.embedding_model:
                embedding = self.embedding_model.encode(content).tolist()
                document.embedding = embedding
            
            # Store in vector database
            if self.collection:
                # Convert metadata to ChromaDB-compatible format
                chroma_metadata = {}
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            chroma_metadata[key] = value
                        else:
                            # Convert complex types to string
                            chroma_metadata[key] = str(value)
                
                self.collection.add(
                    documents=[content],
                    metadatas=[chroma_metadata],
                    embeddings=[document.embedding] if document.embedding else None,
                    ids=[doc_id]
                )
            
            # Cache document
            self.document_cache[doc_id] = document
            
            logger.info(f"Added document {doc_id} to RAG system")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document to RAG: {e}")
            raise
    
    async def search(self, query: str, top_k: int = 5, threshold: float = 0.5) -> List[SearchResult]:
        """Search for relevant documents"""
        try:
            results = []
            
            if not self.collection or not self.embedding_model:
                # Fallback: simple keyword search
                return await self._keyword_search(query, top_k)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in vector database
            search_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Process results
            if search_results['documents']:
                for i, doc_content in enumerate(search_results['documents'][0]):
                    doc_id = search_results['ids'][0][i]
                    metadata = search_results['metadatas'][0][i]
                    distance = search_results['distances'][0][i] if 'distances' in search_results else 0.0
                    
                    # Convert distance to similarity score
                    similarity_score = 1.0 - distance if distance is not None else 0.0
                    
                    if similarity_score >= threshold:
                        document = Document(
                            id=doc_id,
                            content=doc_content,
                            metadata=metadata
                        )
                        
                        result = SearchResult(
                            document=document,
                            similarity_score=similarity_score,
                            relevance_score=similarity_score
                        )
                        results.append(result)
            
            # Sort by relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"RAG search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            return []
    
    async def _keyword_search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Fallback keyword search when embeddings are not available"""
        results = []
        query_lower = query.lower()
        
        for doc_id, document in self.document_cache.items():
            content_lower = document.content.lower()
            
            # Simple keyword matching
            keywords = query_lower.split()
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            
            if matches > 0:
                relevance_score = matches / len(keywords)
                
                result = SearchResult(
                    document=document,
                    similarity_score=relevance_score,
                    relevance_score=relevance_score
                )
                results.append(result)
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]
    
    async def get_context_for_query(self, query: str, max_tokens: int = 2000) -> str:
        """Get relevant context for a query"""
        try:
            # Search for relevant documents
            search_results = await self.search(query, top_k=3, threshold=0.3)
            
            if not search_results:
                return ""
            
            # Build context from search results
            context_parts = []
            current_tokens = 0
            
            for result in search_results:
                if current_tokens >= max_tokens:
                    break
                
                content = result.document.content
                tokens = len(content.split())  # Rough token estimation
                
                if current_tokens + tokens <= max_tokens:
                    context_parts.append(f"**Relevant Context:**\n{content}")
                    current_tokens += tokens
                else:
                    # Truncate if needed
                    remaining_tokens = max_tokens - current_tokens
                    words = content.split()[:remaining_tokens]
                    truncated_content = " ".join(words) + "..."
                    context_parts.append(f"**Relevant Context (truncated):**\n{truncated_content}")
                    break
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context for query: {e}")
            return ""
    
    async def add_conversation_context(self, session_id: str, conversation_history: List[Dict[str, Any]]) -> None:
        """Add conversation history to RAG for context retrieval"""
        try:
            for message in conversation_history[-10:]:  # Last 10 messages
                content = f"{message.get('role', 'unknown')}: {message.get('content', '')}"
                metadata = {
                    "type": "conversation",
                    "session_id": session_id,
                    "timestamp": message.get('timestamp', datetime.now().isoformat()),
                    "role": message.get('role', 'unknown')
                }
                
                await self.add_document(content, metadata)
                
        except Exception as e:
            logger.error(f"Error adding conversation context: {e}")
    
    async def add_script_content(self, script_content: str, metadata: Dict[str, Any] = None) -> str:
        """Add script content to RAG for context retrieval"""
        try:
            doc_metadata = metadata or {}
            doc_metadata.update({
                "type": "script",
                "timestamp": datetime.now().isoformat()
            })
            
            return await self.add_document(script_content, doc_metadata)
            
        except Exception as e:
            logger.error(f"Error adding script content: {e}")
            raise
    
    async def add_tool_result(self, tool_name: str, result: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Add tool execution result to RAG for context retrieval"""
        try:
            content = f"Tool {tool_name} executed with result: {json.dumps(result, indent=2)}"
            doc_metadata = metadata or {}
            doc_metadata.update({
                "type": "tool_result",
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat()
            })
            
            return await self.add_document(content, doc_metadata)
            
        except Exception as e:
            logger.error(f"Error adding tool result: {e}")
            raise
    
    async def get_relevant_tools(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant tools based on query"""
        try:
            # Search for tool-related documents
            search_results = await self.search(query, top_k=5, threshold=0.3)
            
            relevant_tools = []
            for result in search_results:
                if result.document.metadata.get("type") == "tool_result":
                    tool_name = result.document.metadata.get("tool_name")
                    if tool_name and tool_name not in [t["name"] for t in relevant_tools]:
                        relevant_tools.append({
                            "name": tool_name,
                            "relevance_score": result.relevance_score,
                            "last_used": result.document.metadata.get("timestamp")
                        })
            
            return relevant_tools
            
        except Exception as e:
            logger.error(f"Error getting relevant tools: {e}")
            return []
    
    async def clear_session_context(self, session_id: str) -> None:
        """Clear all context for a specific session"""
        try:
            if self.collection:
                # Delete documents for this session
                self.collection.delete(
                    where={"session_id": session_id}
                )
            
            # Remove from cache
            to_remove = [doc_id for doc_id, doc in self.document_cache.items() 
                        if doc.metadata.get("session_id") == session_id]
            
            for doc_id in to_remove:
                del self.document_cache[doc_id]
            
            logger.info(f"Cleared RAG context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing session context: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        try:
            stats = {
                "total_documents": len(self.document_cache),
                "vector_db_available": self.collection is not None,
                "embeddings_available": self.embedding_model is not None,
                "storage_path": str(self.persist_directory)
            }
            
            if self.collection:
                stats["collection_count"] = self.collection.count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting RAG statistics: {e}")
            return {"error": str(e)}

# Global RAG service instance
rag_service = RAGService() 