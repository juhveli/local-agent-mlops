import sys
import os
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock phoenix to avoid connection errors and import side effects
sys.modules["phoenix"] = MagicMock()
sys.modules["phoenix.otel"] = MagicMock()

# Now import the agent
from apps.deep_research.agent import DeepResearchAgent

@pytest.mark.asyncio
async def test_storage_blocking():
    print("Testing DeepResearchAgent storage blocking...")

    # Mock dependencies
    with patch('apps.deep_research.agent.TavilyClient') as MockTavily, \
         patch('apps.deep_research.agent.AsyncOpenAI') as MockAsyncOpenAI, \
         patch('apps.deep_research.agent.DDGS') as MockDDGS, \
         patch('apps.deep_research.agent.trace') as MockTrace: # Mock trace

        # Setup mocks
        mock_tavily_instance = MockTavily.return_value
        mock_tavily_instance.search.return_value = {
            "results": [
                {"title": "Test 1", "url": "http://test1.com", "content": "Test content 1"},
                {"title": "Test 2", "url": "http://test2.com", "content": "Test content 2"},
                {"title": "Test 3", "url": "http://test3.com", "content": "Test content 3"},
                {"title": "Test 4", "url": "http://test4.com", "content": "Test content 4"},
                {"title": "Test 5", "url": "http://test5.com", "content": "Test content 5"},
            ]
        }

        mock_llm_instance = MockAsyncOpenAI.return_value
        mock_llm_instance.chat.completions.create = AsyncMock()
        mock_llm_instance.chat.completions.create.return_value.choices[0].message.content = "Test Answer"

        agent = DeepResearchAgent()

        # Mock decompose_query to avoid LLM call
        agent.decompose_query = AsyncMock(return_value=["test query"])

        # Mock check_relevance to return True immediately
        agent.check_relevance = AsyncMock(return_value=(True, []))

        # Mock synthesize
        agent.synthesize = AsyncMock(return_value="Synthesized Answer")

        # Mock store_knowledge to simulate blocking
        # We need to simulate a slow storage process
        async def slow_store(*args, **kwargs):
            await asyncio.sleep(1.0)
            return

        agent.store_knowledge = AsyncMock(side_effect=slow_store)

        start_time = time.time()
        # Run research
        await agent.research("test query", max_iterations=1, provider="tavily")
        end_time = time.time()

        duration = end_time - start_time
        print(f"Research took {duration:.4f} seconds")

        # It should take minimal time if store_knowledge is non-blocking
        assert duration < 0.2, f"Expected research to be non-blocking (<0.2s), but took {duration:.4f}s"

        # Verify store_knowledge was called
        assert agent.store_knowledge.called
        assert agent.store_knowledge.call_count >= 1

if __name__ == "__main__":
    asyncio.run(test_storage_blocking())
