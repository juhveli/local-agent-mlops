import os
import httpx
from typing import List
from opentelemetry import trace
from dotenv import load_dotenv
from core.observability import get_tracer

load_dotenv()
tracer = get_tracer("embeddings")

class EmbeddingClient:
    """
    Client for generating embeddings using Ollama's API.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model_name = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

    @tracer.start_as_current_span("generate_embeddings")
    def embed(self, text: str) -> List[float]:
        """
        Generates an embedding vector for the given text.
        """
        span = trace.get_current_span()
        span.set_attribute("embedding.model", self.model_name)
        
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_name,
            "prompt": text
        }
        
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        
        vector = response.json().get("embedding")
        span.set_attribute("embedding.dimension", len(vector))
        return vector

if __name__ == "__main__":
    from core.observability import init_observability
    from opentelemetry import trace
    
    init_observability()
    client = EmbeddingClient()
    print(f"Testing embedding with {client.model_name}...")
    try:
        vec = client.embed("NornicDB is awesome.")
        print(f"Success! Vector length: {len(vec)}")
    except Exception as e:
        print(f"Error: {e}")
