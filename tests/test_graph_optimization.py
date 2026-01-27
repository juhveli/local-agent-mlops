import sys
import os
import asyncio
from unittest.mock import MagicMock, patch
from collections import namedtuple

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.api.main import get_memory_graph

async def test_get_memory_graph_performance_logic():
    print("Testing get_memory_graph logic...")

    # Patch the global client instance directly
    with patch('apps.api.main.nornic_client') as client:
        client.use_fallback = False
        client.qdrant = MagicMock()

        # Mock Neo4j session to return NOTHING so we rely on Qdrant which has 'query' metadata
        client.driver.session.return_value.__enter__.return_value.run.side_effect = [
            [], # First call for nodes (empty)
            [] # Second call for existing relationships (empty)
        ]

        # Mock Qdrant scroll result with nodes that have 'query' metadata
        points = []
        Point = namedtuple('Point', ['id', 'payload'])
        for i in range(100):
            q_idx = i // 50
            points.append(Point(
                id=f"node_{i}",
                payload={
                    "query": f"query_{q_idx}",
                    "url": f"http://example.com/{i}",
                    "content": f"content {i}"
                }
            ))

        client.qdrant.scroll.return_value = [points, None]

        # Now run the function
        result = get_memory_graph()

        links = result["links"]
        nodes = result["nodes"]

        print(f"Generated {len(links)} links for {len(nodes)} nodes.")

        # Verify link count
        assert len(links) < 200, f"Too many links generated: {len(links)}. Expected O(N)."
        assert len(links) >= 98, f"Too few links generated: {len(links)}. Expected connectivity."

        # Verify connectivity type
        same_query_links = [l for l in links if l["type"] == "same_query"]
        assert len(same_query_links) == 98, f"Expected 98 same_query links, got {len(same_query_links)}"

        print("Test passed: Graph generation is optimized.")

if __name__ == "__main__":
    asyncio.run(test_get_memory_graph_performance_logic())
