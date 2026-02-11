import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables
os.environ["TAVILY_API_KEY"] = "mock-key"
os.environ["LM_STUDIO_URL"] = "http://mock-lm-studio/v1"

# Setup Mocks
mock_openai = MagicMock()
sys.modules["openai"] = mock_openai
sys.modules["tavily"] = MagicMock()
sys.modules["duckduckgo_search"] = MagicMock()
sys.modules["phoenix"] = MagicMock()
sys.modules["phoenix.otel"] = MagicMock()
# We need to mock opentelemetry carefully because of decorators
mock_otel = MagicMock()
sys.modules["opentelemetry"] = mock_otel
mock_trace = MagicMock()
sys.modules["opentelemetry.trace"] = mock_trace

# Configure Tracer Mock
mock_tracer = MagicMock()

def mock_start_span(name):
    class ContextDecorator(MagicMock):
        def __call__(self, func):
            return func
        def __enter__(self):
            return MagicMock()
        def __exit__(self, *args):
            pass
    return ContextDecorator()

mock_tracer.start_as_current_span.side_effect = mock_start_span
mock_trace.get_tracer.return_value = mock_tracer
mock_otel.trace.get_tracer.return_value = mock_tracer


# Mock httpx
sys.modules["httpx"] = MagicMock()

# Setup AsyncOpenAI to return AsyncMock instance
mock_client_instance = AsyncMock()
mock_openai.AsyncOpenAI.return_value = mock_client_instance

# Mock response
mock_response = MagicMock()
mock_response.choices = [MagicMock(message=MagicMock(content="Mock answer", reasoning_content="Mock thought"))]
mock_response.id = "mock-response-id"

# The create method should return an awaitable that resolves to mock_response
async def mock_create(*args, **kwargs):
    return mock_response

mock_client_instance.chat.completions.create = mock_create

# Patch imports that happen inside functions or modules
with patch("neo4j.GraphDatabase.driver"), \
     patch("qdrant_client.QdrantClient"), \
     patch("qdrant_client.AsyncQdrantClient"):

    # Import modules under test
    from core.inference import get_shared_inference_client, InferenceClient
    from apps.chat.agent import ChatAgent
    from core.ingestion import PDFIngestor

    async def test_inference():
        print("Testing AsyncInferenceClient...")
        client = get_shared_inference_client()

        content, thought, rid = await client.chat("Test prompt")
        print(f"Result: {content}, {thought}, {rid}")
        assert content == "Mock answer"
        assert rid == "mock-response-id"
        print("✅ InferenceClient passed")

    async def test_chat_agent():
        print("Testing ChatAgent...")
        agent = ChatAgent()
        # Mock _retrieve_context to avoid Nornic logic
        # We need to mock it on the instance
        agent._retrieve_context = MagicMock(return_value=[{"content": "context", "url": "url"}])

        response = await agent.chat("User message")
        assert response == "Mock answer"
        assert agent.last_response_id == "mock-response-id"

        print("✅ ChatAgent passed")

    async def test_ingestion():
        print("Testing PDFIngestor...")
        ingestor = PDFIngestor()

        # Mock _pdf_to_images
        ingestor._pdf_to_images = MagicMock(return_value=["base64img"])

        # Mock _chunk_text
        ingestor._chunk_text = MagicMock(return_value=["chunk1"])
        # Mock nornic upsert
        ingestor.nornic_client.upsert_knowledge = MagicMock()

        # Mock get_embedding
        with patch("core.ingestion.get_embedding", return_value=[0.1, 0.2]):
             count = await ingestor.process(b"pdf-bytes", "test.pdf")
             assert count == 1

        print("✅ PDFIngestor passed")

    async def main():
        await test_inference()
        await test_chat_agent()
        await test_ingestion()

    if __name__ == "__main__":
        asyncio.run(main())
