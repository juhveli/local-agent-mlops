import inspect
import sys
import os
from unittest.mock import MagicMock

# Set mock env vars before importing anything that might use them
os.environ["TAVILY_API_KEY"] = "mock-key"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"
os.environ["QDRANT_URL"] = "http://localhost:6333"

# Add root to sys.path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after setting env vars
from apps.api.main import chat, get_memory_graph

def test_chat_is_sync():
    """
    Verify that the chat endpoint is defined as a synchronous function (`def`).
    Since it performs blocking I/O (LLM calls via requests), it must NOT be `async def`.
    FastAPI runs `def` endpoints in a thread pool, preventing the event loop from blocking.
    """
    assert not inspect.iscoroutinefunction(chat), "chat endpoint should be synchronous def to avoid blocking event loop"

def test_get_memory_graph_is_sync():
    """
    Verify that the get_memory_graph endpoint is defined as a synchronous function (`def`).
    Since it performs blocking DB calls (Neo4j driver), it must NOT be `async def`.
    """
    assert not inspect.iscoroutinefunction(get_memory_graph), "get_memory_graph endpoint should be synchronous def to avoid blocking event loop"
