import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv
from core.observability import get_tracer

load_dotenv()
tracer = get_tracer("nornic_db")

class NornicClient:
    """
    Client for interacting with NornicDB (Neo4j + Qdrant).
    """
    
    def __init__(self):
        # Neo4j config
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.use_fallback = False
        self.fallback_file = "nornic_fallback.json"
        
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            # Qdrant config
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            self.qdrant = QdrantClient(url=qdrant_url, timeout=5)
            self.collection_name = "knowledge_base"
            self._init_qdrant()
            print("✅ Connected to NornicDB (Neo4j + Qdrant)")
        except Exception as e:
            print(f"⚠️ NornicDB connection failed: {e}. Switching to Local Fallback.")
            self.use_fallback = True
            self.driver = None
            self.qdrant = None

    def _init_qdrant(self):
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE) # Nomic-embed dim
            )

    @tracer.start_as_current_span("nornic_upsert")
    def upsert_knowledge(self, content: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Stores content in Qdrant and creates a node in Neo4j (or fallback).
        """
        doc_id = metadata.get("id", str(hash(content)))
        
        if self.use_fallback:
            self._upsert_fallback(content, metadata)
            return

        # 1. Store in Qdrant
        try:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload={"content": content, **metadata}
                    )
                ]
            )
        except Exception:
            self._upsert_fallback(content, metadata)
            return
        
        # 2. Store in Neo4j
        with self.driver.session() as session:
            session.execute_write(self._create_node, doc_id, content, metadata)

    def _upsert_fallback(self, content: str, metadata: Dict[str, Any]):
        import json
        data = []
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r") as f:
                    data = json.load(f)
            except: pass
        
        data.append({"content": content, "metadata": metadata})
        with open(self.fallback_file, "w") as f:
            json.dump(data[-100:], f) # Keep last 100

    @staticmethod
    def _create_node(tx, doc_id, content, metadata):
        query = (
            "MERGE (d:Document {id: $id}) "
            "SET d.content = $content, d.url = $url, d.timestamp = timestamp() "
            "RETURN d"
        )
        tx.run(query, id=doc_id, content=content[:200], url=metadata.get("url", "unknown"))

    @tracer.start_as_current_span("nornic_upsert_batch")
    def upsert_knowledge_batch(self, items: List[Dict[str, Any]]):
        """
        Batch stores content in Qdrant and Neo4j.
        items: List of dicts with keys: 'content', 'vector', 'metadata'
        """
        if not items:
            return

        if self.use_fallback:
            for item in items:
                self._upsert_fallback(item["content"], item["metadata"])
            return

        points = []
        neo4j_params = []

        for item in items:
            content = item["content"]
            vector = item["vector"]
            metadata = item["metadata"]
            doc_id = metadata.get("id", str(hash(content)))

            points.append(PointStruct(
                id=doc_id,
                vector=vector,
                payload={"content": content, **metadata}
            ))

            neo4j_params.append({
                "id": doc_id,
                "content": content[:200],
                "url": metadata.get("url", "unknown")
            })

        # 1. Store in Qdrant
        try:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            print(f"Qdrant batch upsert failed: {e}")
            for item in items:
                self._upsert_fallback(item["content"], item["metadata"])
            return

        # 2. Store in Neo4j
        try:
            with self.driver.session() as session:
                session.execute_write(self._create_nodes_batch, neo4j_params)
        except Exception as e:
            print(f"Neo4j batch upsert failed: {e}")

    @staticmethod
    def _create_nodes_batch(tx, params_list):
        query = (
            "UNWIND $batch AS row "
            "MERGE (d:Document {id: row.id}) "
            "SET d.content = row.content, d.url = row.url, d.timestamp = timestamp()"
        )
        tx.run(query, batch=params_list)

    @tracer.start_as_current_span("nornic_query")
    def hybrid_search(self, vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs vector search in Qdrant. 
        Note: In a full GraphRAG, this would also query Neo4j for related nodes.
        """
        if self.use_fallback or self.qdrant is None:
            return []

        try:
            results = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit
            )
            return [point.payload for point in results.points]
        except Exception as e:
            print(f"[Warning] Qdrant search failed: {e}")
            return []

    def close(self):
        self.driver.close()

if __name__ == "__main__":
    # Test would require running infra
    client = NornicClient()
    print("NornicClient initialized.")
    client.close()
