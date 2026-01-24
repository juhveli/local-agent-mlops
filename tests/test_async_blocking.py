import inspect
import sys
import os
from unittest.mock import MagicMock, patch

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force import of modules to ensure they are available for patching
# This handles the namespace package issue where 'agent' might not be attached to 'apps.deep_research'
try:
    import apps.deep_research.agent
    import apps.chat.agent
    import core.nornic_client
    import core.ingestion
except ImportError as e:
    print(f"ImportError during setup: {e}")

def test_endpoints_are_blocking_async():
    with patch('apps.deep_research.agent.DeepResearchAgent') as MockDRA, \
         patch('apps.chat.agent.ChatAgent') as MockCA, \
         patch('core.nornic_client.NornicClient') as MockNC, \
         patch('core.ingestion.PDFIngestor') as MockPI:

        from apps.api.main import chat, get_memory_graph, clear_chat, run_research

        print("\nChecking endpoint definitions...")

        is_chat_async = inspect.iscoroutinefunction(chat)
        is_graph_async = inspect.iscoroutinefunction(get_memory_graph)
        is_clear_async = inspect.iscoroutinefunction(clear_chat)
        is_research_async = inspect.iscoroutinefunction(run_research)

        print(f"Chat Endpoint Async: {is_chat_async}")
        print(f"Graph Endpoint Async: {is_graph_async}")
        print(f"Clear Chat Endpoint Async: {is_clear_async}")
        print(f"Research Endpoint Async: {is_research_async}")

        # Assert OPTIMIZED state (expecting sync handlers for threadpool offloading)
        assert is_chat_async is False, "Expected chat to be SYNC (optimized)"
        assert is_graph_async is False, "Expected get_memory_graph to be SYNC (optimized)"
        assert is_clear_async is False, "Expected clear_chat to be SYNC (optimized)"
        assert is_research_async is True, "Expected run_research to be ASYNC (unchanged)"

if __name__ == "__main__":
    test_endpoints_are_blocking_async()
