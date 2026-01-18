# Bolt's Journal

## 2024-05-22 - Initial Setup
**Learning:** Bolt needs a journal to track critical learnings.
**Action:** Created this file.

## 2024-05-22 - Graph Generation Bottleneck
**Learning:** `apps/api/main.py` generates graph links using an O(n^2) nested loop within `get_memory_graph`. This occurs for both "same_query" and "same_domain" groups. While current limits (100 nodes) mask this, scaling the node count will degrade performance significantly.
**Action:** When optimizing the backend or increasing node limits, refactor this to use a more efficient graph construction method or process relationships in the database/vector store directly.
