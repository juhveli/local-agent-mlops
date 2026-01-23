import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.deep_research.agent import DeepResearchAgent

async def test_agent_params():
    print("Testing DeepResearchAgent params...")

    # Mock LLM and Tavily
    with patch('apps.deep_research.agent.TavilyClient') as MockTavily, \
         patch('apps.deep_research.agent.AsyncOpenAI') as MockAsyncOpenAI, \
         patch('apps.deep_research.agent.DDGS') as MockDDGS:

        # Setup mocks
        mock_tavily_instance = MockTavily.return_value
        mock_tavily_instance.search.return_value = {"results": [{"title": "Test", "url": "http://test.com", "content": "Test content"}]}

        mock_llm_instance = MockAsyncOpenAI.return_value
        # Mock async create method
        mock_llm_instance.chat.completions.create = AsyncMock()
        mock_llm_instance.chat.completions.create.return_value.choices[0].message.content = "Test Answer"

        agent = DeepResearchAgent()

        # Test 1: Tavily Basic
        print("1. Testing Tavily Basic...")
        await agent.research("test query", max_iterations=1, provider="tavily", search_depth="basic")
        mock_tavily_instance.search.assert_called_with(query="test query", max_results=3, include_raw_content=True, search_depth="basic")
        print("   Passed.")

        # Test 2: Tavily Advanced
        print("2. Testing Tavily Advanced...")
        # Since decompose_query is now async, we use AsyncMock
        with patch.object(agent, 'decompose_query', new_callable=AsyncMock) as mock_decompose:
            mock_decompose.return_value = ["test query"]
            await agent.research("test query", max_iterations=1, provider="tavily", search_depth="advanced")
            mock_tavily_instance.search.assert_called_with(query="test query", max_results=3, include_raw_content=True, search_depth="advanced")
        print("   Passed.")

        # Test 3: DuckDuckGo
        print("3. Testing DuckDuckGo...")
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"title": "DDG Test", "href": "http://ddg.com", "body": "DDG Content"}]

        with patch.object(agent, 'decompose_query', new_callable=AsyncMock) as mock_decompose:
            mock_decompose.return_value = ["test query"]
            await agent.research("test query", max_iterations=1, provider="duckduckgo")
            mock_ddgs_instance.text.assert_called()
        print("   Passed.")

if __name__ == "__main__":
    asyncio.run(test_agent_params())
