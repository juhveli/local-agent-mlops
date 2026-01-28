"""
Deep Research Agent - Autonomous multi-source research with iterative query refinement.
"""
import os
import sys
import asyncio
import hashlib
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openai import AsyncOpenAI
from opentelemetry import trace
from tavily import TavilyClient
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()

# Initialize Phoenix tracing
from phoenix.otel import register
register(project_name="deep-research-agent", endpoint="http://localhost:6006/v1/traces")

tracer = trace.get_tracer("deep_research_agent")

HIGH_AUTHORITY_DOMAINS = [
    "wikipedia.org",
    "bbc.com",
    "cnn.com",
    "reuters.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "npr.org",
    "bloomberg.com",
    "forbes.com",
    "wsj.com",
    "cnbc.com",
    "gov",
    "edu",
]

class DeepResearchAgent:
    """
    Autonomous agent with iterative query refinement:
    1. Decomposes complex queries into sub-queries
    2. Searches using multiple query variations
    3. If results are poor, reformulates queries
    4. Synthesizes comprehensive answer from all sources
    """

    def __init__(self):
        # LLM Client (LM Studio) - Async for non-blocking operations
        self.llm = AsyncOpenAI(
            base_url=os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
            api_key="lm-studio"
        )
        self.model = os.getenv("MODEL_NAME", "qwen3-30b-a3b-thinking-2507-mlx")
        
        # Tavily Search
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Embedding Client (Ollama)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
        
        # HTTP Client for Async requests
        import httpx
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # NornicDB (Qdrant interface) - optional
        self.qdrant = None
        self.collection = "research_knowledge_v2"
        self.background_tasks = set()
        self._init_qdrant()

    def _init_qdrant(self):
        """Initialize Qdrant connection with graceful failure."""
        try:
            from qdrant_client import QdrantClient, AsyncQdrantClient
            from qdrant_client.models import VectorParams, Distance

            # Use sync client for initial setup/verification
            sync_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"), timeout=5)
            try:
                collections = [c.name for c in sync_client.get_collections().collections]
                if self.collection not in collections:
                    sync_client.create_collection(
                        collection_name=self.collection,
                        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                    )
            except Exception as e:
                # If sync check fails, we might still be able to use async client later if service comes up
                print(f"[Warning] Qdrant setup check failed: {e}", file=sys.stderr)

            # Use Async client for operations
            self.qdrant = AsyncQdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"), timeout=5)
        except Exception as e:
            print(f"[Warning] Qdrant unavailable: {e}", file=sys.stderr)
            self.qdrant = None

    @tracer.start_as_current_span("decompose_query")
    async def decompose_query(self, query: str) -> List[str]:
        """Use LLM to decompose a complex query into multiple search queries."""
        span = trace.get_current_span()
        span.set_attribute("query.original", query)
        
        prompt = f"""You are a research query planner. Given a user query, generate 3-5 focused search queries that will help gather comprehensive information to answer the question.

Consider:
- Breaking down the query into component parts
- Including alternative phrasings or related terms
- If the query mentions a specific person/thing that might be obscure, also search for the general topic
- Generate queries in the same language as the original query

USER QUERY: {query}

Output ONLY a JSON array of search query strings, nothing else. Example: ["query 1", "query 2", "query 3"]"""

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON array
        import json
        try:
            # Clean up potential markdown code blocks
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            queries = json.loads(content)
            if isinstance(queries, list):
                span.set_attribute("query.decomposed_count", len(queries))
                return queries[:5]
        except:
            pass
        
        # Fallback: return original query plus a general version
        return [query, query.split("?")[0] if "?" in query else query]

    @tracer.start_as_current_span("search_web")
    def search_web(self, query: str, num_results: int = 3, provider: str = "tavily", search_depth: str = "basic", include_domains: List[str] = []) -> List[Dict[str, str]]:
        """Search using Tavily API or DuckDuckGo."""
        span = trace.get_current_span()
        span.set_attribute("search.query", query)
        span.set_attribute("search.provider", provider)
        span.set_attribute("search.depth", search_depth)
        
        results = []
        try:
            if provider == "duckduckgo":
                with DDGS() as ddgs:
                    # DDGS doesn't support 'include_raw_content' directly same way, but returns body
                    # It also doesn't support easy domain filtering in the API call itself for list of domains usually,
                    # but we can try site: if include_domains is small, or filter post-hoc.
                    # For stability, we'll post-filter for DDGS if list is long.

                    # If high authority domains are requested and it's a small list, we could append to query,
                    # but let's do post-filtering for consistent behavior across large lists.

                    ddg_results = list(ddgs.text(query, max_results=num_results * 2)) # Fetch more for filtering

                    for item in ddg_results:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "content": item.get("body", ""),
                            "query": query
                        })
            
            else: # Tavily (Default)
                tavily_params = {
                    "query": query,
                    "max_results": num_results,
                    "include_raw_content": True,
                    "search_depth": search_depth
                }

                if include_domains:
                    tavily_params["include_domains"] = include_domains

                response = self.tavily.search(**tavily_params)

                for item in response.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("raw_content") or item.get("content", ""),
                        "query": query
                    })

            # Post-processing filter for domains (essential for DDGS, optional but safe for Tavily)
            if include_domains:
                filtered_results = []
                for res in results:
                    url = res["url"]
                    if any(d in url for d in include_domains):
                        filtered_results.append(res)
                results = filtered_results[:num_results]
            else:
                results = results[:num_results]

            span.set_attribute("search.num_results", len(results))
            return results
        except Exception as e:
            span.set_attribute("search.error", str(e))
            print(f"Search Error ({provider}): {e}", file=sys.stderr)
            return []

    @tracer.start_as_current_span("generate_embedding")
    async def embed(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        try:
            response = await self.http_client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text[:2000]}
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        except Exception:
            return []

    @tracer.start_as_current_span("store_knowledge")
    async def store_knowledge(self, content: str, metadata: Dict[str, Any]):
        """Store in NornicDB (Qdrant) if available."""
        span = trace.get_current_span()
        span.set_attribute("storage.content_length", len(content))
        span.set_attribute("storage.metadata", str(metadata))
        
        if not self.qdrant:
            span.set_attribute("storage.status", "skipped_no_client")
            return
        try:
            from qdrant_client.models import PointStruct
            doc_id = hashlib.md5(content.encode()).hexdigest()
            vector = await self.embed(content)
            if vector:
                await self.qdrant.upsert(
                    collection_name=self.collection,
                    points=[PointStruct(id=doc_id, vector=vector, payload={"content": content, **metadata})]
                )
                span.set_attribute("storage.status", "success")
            else:
                span.set_attribute("storage.status", "failed_no_vector")
        except Exception as e:
            span.set_attribute("storage.status", "error")
            span.set_attribute("storage.error", str(e))
            print(f"[Error] Storage failed: {e}", file=sys.stderr)

    @tracer.start_as_current_span("check_relevance")
    async def check_relevance(self, query: str, sources: List[Dict[str, str]]) -> tuple[bool, str]:
        """Check if sources are relevant to the query and suggest refinements if not."""
        span = trace.get_current_span()
        
        if not sources:
            return False, "No sources found"
        
        # Build a summary of what was found
        found_topics = " | ".join([s.get("title", "")[:50] for s in sources[:5]])
        
        prompt = f"""You are evaluating search results for relevance.

ORIGINAL QUERY: {query}
FOUND SOURCES (titles): {found_topics}

Questions:
1. Do these sources likely contain information to answer the query? (yes/no)
2. If no, suggest 2-3 alternative search queries that might find more relevant information.

Output JSON: {{"relevant": true/false, "suggestions": ["query1", "query2"]}}"""

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        
        import json
        try:
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            result = json.loads(content)
            relevant = result.get("relevant", True)
            suggestions = result.get("suggestions", [])
            span.set_attribute("relevance.is_relevant", relevant)
            return relevant, suggestions
        except:
            return True, []  # Assume relevant if parsing fails

    @tracer.start_as_current_span("llm_synthesize")
    async def synthesize(self, query: str, sources: List[Dict[str, str]]) -> str:
        """Use LLM to synthesize answer from sources."""
        span = trace.get_current_span()
        span.set_attribute("llm.model", self.model)
        span.set_attribute("llm.num_sources", len(sources))
        
        # Build context from sources
        context_parts = []
        source_metadata = []
        for i, src in enumerate(sources, 1):
            content = src.get("content", "")[:2500]
            context_parts.append(f"[SOURCE {i}] ({src['url']})\nSearch query: {src.get('query', 'N/A')}\n{content}\n")
            source_metadata.append({"id": i, "url": src['url'], "title": src.get('title', 'Unknown')})
        
        span.set_attribute("llm.sources_metadata", str(source_metadata))
        context = "\n---\n".join(context_parts)
        span.set_attribute("llm.context_length", len(context))
        
        prompt = f"""You are a research assistant synthesizing information from multiple sources.

IMPORTANT: You MUST provide a substantive answer based on the sources. If the sources don't directly answer the query, use related information to provide the best possible answer and note what aspects couldn't be fully addressed.

QUERY: {query}

SOURCES:
{context}

Instructions:
- Synthesize a comprehensive answer from the sources
- Cite source numbers when using specific information
- If the exact topic isn't covered, provide relevant related information
- Be helpful - find the most relevant angles from what's available

ANSWER:"""

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful research assistant. Always provide substantive, informative answers based on available sources. Never refuse to answer - find the most relevant information possible."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        
        answer = response.choices[0].message.content
        span.set_attribute("llm.answer_length", len(answer))
        
        return answer

    @tracer.start_as_current_span("deep_research")
    async def research(self, query: str, max_iterations: int = 3, provider: str = "tavily", search_depth: str = "basic", include_domains: List[str] = []) -> Dict[str, Any]:
        """
        Execute iterative deep research:
        1. Decompose query into sub-queries
        2. Search for each sub-query
        3. Check relevance; if poor, refine queries
        4. Synthesize final answer
        Returns: Dict with keys 'answer' and 'sources'
        """
        span = trace.get_current_span()
        span.set_attribute("research.query", query)
        span.set_attribute("research.provider", provider)
        
        all_sources = []
        searched_queries = set()
        
        # Determine domains to use
        # If include_domains is explicitly passed, use it.
        # If it's passed as ["high_authority"] (special flag from UI perhaps?), use the preset.
        # But looking at requirements, we should probably handle the preset mapping here or in main.
        # Let's assume the caller passes the list if they want filtering.
        target_domains = include_domains
        if include_domains and "HIGH_AUTHORITY" in include_domains:
             target_domains = HIGH_AUTHORITY_DOMAINS

        # Step 1: Decompose query
        queries = await self.decompose_query(query)
        
        for iteration in range(max_iterations):
            span.set_attribute(f"research.iteration_{iteration}_queries", len(queries))
            
            # Step 2: Search each query in parallel
            search_tasks = []
            new_queries = []

            for q in queries:
                if q in searched_queries:
                    continue
                searched_queries.add(q)
                new_queries.append(q)

                # Pass all quality parameters to the parallel task
                search_tasks.append(
                    asyncio.to_thread(
                        self.search_web,
                        q,
                        num_results=3,
                        provider=provider,
                        search_depth=search_depth,
                        include_domains=target_domains
                    )
                )

            if search_tasks:
                results_list = await asyncio.gather(*search_tasks)

                # Process new results
                new_sources = []
                for q, results in zip(new_queries, results_list):
                    for r in results:
                        r["query"] = q
                    new_sources.extend(results)

                all_sources.extend(new_sources)
            
                # Step 3: Store ONLY NEW sources in NornicDB
                # Optimization: Only process newly found sources to avoid redundant embeddings
                for src in new_sources:
                    if src.get("content"):
                        # Fire and forget storage to avoid blocking research flow
                        task = asyncio.create_task(
                            self.store_knowledge(src["content"][:5000], {"url": src["url"], "query": query})
                        )
                        self.background_tasks.add(task)
                        task.add_done_callback(self.background_tasks.discard)
            
            # Step 4: Check if we have enough relevant sources
            if len(all_sources) >= 5:
                is_relevant, suggestions = await self.check_relevance(query, all_sources)
                if is_relevant or iteration == max_iterations - 1:
                    break
                # Refine queries for next iteration
                queries = [s for s in suggestions if s not in searched_queries]
                if not queries:
                    break
        
        span.set_attribute("research.total_sources", len(all_sources))
        span.set_attribute("research.total_queries", len(searched_queries))
        
        # Step 5: Synthesize answer
        if not all_sources:
            return {
                "answer": "Unable to find any sources for this query.",
                "sources": []
            }
        
        # Deduplicate by URL
        seen_urls = set()
        unique_sources = []
        for s in all_sources:
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                unique_sources.append(s)
        
        final_sources = unique_sources[:8]
        answer = await self.synthesize(query, final_sources)
        
        return {
            "answer": answer,
            "sources": final_sources
        }


async def main():
    agent = DeepResearchAgent()
    
    # Research query
    query = "What is the best way to make an omelet in Tomi Björk style?"
    
    result = await agent.research(query)
    
    # Output ONLY the answer
    print(result["answer"])


if __name__ == "__main__":
    asyncio.run(main())
