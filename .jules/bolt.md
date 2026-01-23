# Bolt's Journal

## 2024-05-22 - Initial Setup
**Learning:** Bolt needs a journal to track critical learnings.
**Action:** Created this file.

## 2024-05-22 - Graph Generation Bottleneck
**Learning:** `apps/api/main.py` generates graph links using an O(n^2) nested loop within `get_memory_graph`. This occurs for both "same_query" and "same_domain" groups. While current limits (100 nodes) mask this, scaling the node count will degrade performance significantly.
**Action:** When optimizing the backend or increasing node limits, refactor this to use a more efficient graph construction method or process relationships in the database/vector store directly.

## 2024-05-22 - Graph Generation Optimized
**Learning:** Replaced O(n^2) clique generation with O(n) sequential chain linking in `get_memory_graph`. This reduces edge count by >95% for dense groups (e.g. 50 nodes: 1225 -> 49 edges) and significantly improves response time and frontend rendering performance.
**Action:** Always prefer linear connectivity (chains/trees) over full cliques for visualization graphs unless explicit pairwise relationships are required.

## 2024-05-23 - LLM Client Instantiation Overhead
**Learning:** The `generate_response` helper in `core/inference.py` was instantiating a new `InferenceClient` (and thus a new `OpenAI`/`httpx` client) for every request. This defeats HTTP connection pooling (keep-alive), causing unnecessary latency from repeated TCP/SSL handshakes.
**Action:** Implemented a singleton pattern for `InferenceClient` to reuse the underlying connection pool. Always check helper functions for hidden expensive object instantiations.

## 2024-05-23 - Async Event Loop Blocking
**Learning:** The `DeepResearchAgent` was calling synchronous LLM methods (`OpenAI` client) inside `async` methods. This blocked the entire asyncio event loop for the duration of the LLM call (seconds), preventing other concurrent tasks (e.g., heartbeats, other API requests) from running.
**Action:** Refactored `DeepResearchAgent` to use `AsyncOpenAI` and await all LLM calls. Always ensure I/O bound operations in async paths use non-blocking async libraries.
