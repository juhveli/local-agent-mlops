import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.deep_research.agent import DeepResearchAgent

async def test_agent_params():
    print("Testing DeepResearchAgent params...")

    # Mock LLM and Tavily
    with patch('apps.deep_research.agent.TavilyClient') as MockTavily, \
         patch('apps.deep_research.agent.OpenAI') as MockOpenAI, \
         patch('apps.deep_research.agent.DDGS') as MockDDGS:

        # Setup mocks
        mock_tavily_instance = MockTavily.return_value
        mock_tavily_instance.search.return_value = {"results": [{"title": "Test", "url": "http://test.com", "content": "Test content"}]}

        mock_llm_instance = MockOpenAI.return_value
        mock_llm_instance.chat.completions.create.return_value.choices[0].message.content = "Test Answer"

        agent = DeepResearchAgent()

        # Test 1: Tavily Basic
        print("1. Testing Tavily Basic...")
        await agent.research("test query", max_iterations=1, provider="tavily", search_depth="basic")
        mock_tavily_instance.search.assert_called_with(query="test query", max_results=3, include_raw_content=True, search_depth="basic")
        print("   Passed.")

        # Test 2: Tavily Advanced
        print("2. Testing Tavily Advanced...")
        await agent.research("test query", max_iterations=1, provider="tavily", search_depth="advanced")
        # Note: decompose_query is called, which calls search_web for each subquery.
        # But here we are checking if search_web calls tavily with correct params.
        # Since decompose_query might return multiple queries, we look at the last call or any call.
        # However, decompose_query mocks return string, so it probably just returns ["test query", ...]
        # Let's mock decompose_query to return just the original query to be sure.
        with patch.object(agent, 'decompose_query', return_value=["test query"]):
             await agent.research("test query", max_iterations=1, provider="tavily", search_depth="advanced")
             mock_tavily_instance.search.assert_called_with(query="test query", max_results=3, include_raw_content=True, search_depth="advanced")
        print("   Passed.")

        # Test 3: DuckDuckGo
        print("3. Testing DuckDuckGo...")
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"title": "DDG Test", "href": "http://ddg.com", "body": "DDG Content"}]

        with patch.object(agent, 'decompose_query', return_value=["test query"]):
             await agent.research("test query", max_iterations=1, provider="duckduckgo")
             mock_ddgs_instance.text.assert_called()
        print("   Passed.")

if __name__ == "__main__":
    asyncio.run(test_agent_params())
