import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from collections import defaultdict
from urllib.parse import urlparse

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.deep_research.agent import DeepResearchAgent
from apps.chat.agent import ChatAgent
from apps.api.models import ResearchRequest, ResearchResponse, ChatRequest, ChatResponse

app = FastAPI(title="Local Agent MLOps API")

# Configure CORS for React frontend (Vite defaults to port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "deep-research-agent"}

@app.post("/api/research", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    """
    Execute a deep research task and return the final answer.
    """
    try:
        agent = DeepResearchAgent()
        # Note: The current agent implementation parses sources internally.
        # Ideally, we would refactor the agent to return structured data.
        # For this MVP, we will invoke the agent and since we don't have easy access 
        # to the internal intermediate state without refactoring, we'll return the text answer.
        # Future improvement: Refactor agent.research to return (answer, sources) tuple.
        
        result = await agent.research(
            request.query,
            max_iterations=request.max_iterations,
            provider=request.provider,
            search_depth=request.search_depth,
            include_domains=request.include_domains
        )
        
        # Map raw source dicts to Source model
        sources_list = []
        for i, s in enumerate(result.get("sources", []), 1):
            sources_list.append({
                "id": i,
                "url": s.get("url", ""),
                "title": s.get("title", "Unknown"),
                "content": s.get("content", "")[:500], # Truncate for API
                "query": s.get("query", "")
            })

        return ResearchResponse(
            answer=result["answer"],
            sources=sources_list,
            trace_id="trace-id-placeholder" 
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat agent instance (shared for conversation memory)
chat_agent = ChatAgent()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the GraphRAG chat agent.
    """
    try:
        response = chat_agent.chat(request.message)
        return ChatResponse(
            message=response,
            sources_used=len(chat_agent._retrieve_context(request.message, limit=3))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/clear")
async def clear_chat():
    """
    Clear the chat conversation history.
    """
    chat_agent.clear_history()
    return {"status": "ok", "message": "Chat history cleared"}


@app.get("/api/memory/graph")
async def get_memory_graph():
    """
    Fetch knowledge graph data for visualization.
    Returns nodes and links from NornicDB.
    """
    from core.nornic_client import NornicClient
    
    try:
        client = NornicClient()
        
        nodes = []
        links = []
        
        if client.use_fallback:
            # Fallback: Load from JSON file
            import json
            if os.path.exists(client.fallback_file):
                with open(client.fallback_file, "r") as f:
                    data = json.load(f)
                for i, item in enumerate(data):
                    nodes.append({
                        "id": str(i),
                        "name": item.get("metadata", {}).get("url", f"Document {i}")[:50],
                        "content": item.get("content", "")[:200],
                        "group": 1
                    })
        else:
            # Query Neo4j for Document nodes
            with client.driver.session() as session:
                result = session.run(
                    "MATCH (d:Document) RETURN d.id AS id, d.content AS content, d.url AS url LIMIT 100"
                )
                for i, record in enumerate(result):
                    nodes.append({
                        "id": record["id"] or str(i),
                        "name": (record["url"] or f"Document {i}")[:50],
                        "content": (record["content"] or "")[:200],
                        "group": 1
                    })
                
                # Query relationships
                rel_result = session.run(
                    "MATCH (a:Document)-[r]->(b:Document) RETURN a.id AS source, b.id AS target, type(r) AS type LIMIT 200"
                )
                for record in rel_result:
                    links.append({
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"]
                    })
        
        # Also fetch from Qdrant if available
        # Note: Deep Research Agent stores to 'research_knowledge_v2' collection
        research_collection = "research_knowledge_v2"
        node_queries = {}  # Track which query each node came from
        
        if client.qdrant and not client.use_fallback:
            try:
                scroll_result = client.qdrant.scroll(
                    collection_name=research_collection,
                    limit=100,
                    with_payload=True,
                    with_vectors=False
                )
                for point in scroll_result[0]:
                    payload = point.payload or {}
                    node_id = str(point.id)
                    query = payload.get("query", "")
                    url = payload.get("url", "")
                    
                    # Extract domain for grouping
                    domain = ""
                    if url:
                        try:
                            domain = urlparse(url).netloc
                        except:
                            pass
                    
                    if not any(n["id"] == node_id for n in nodes):
                        nodes.append({
                            "id": node_id,
                            "name": url[:50] if url else f"Vector {node_id}",
                            "content": payload.get("content", "")[:200],
                            "query": query,
                            "domain": domain,
                            "group": 2
                        })
                        node_queries[node_id] = query
            except Exception:
                pass  # Qdrant might not have data yet
        
        # Generate links based on shared queries and domain similarity
        
        # Group nodes by query
        query_to_nodes = defaultdict(list)
        for node in nodes:
            q = node.get("query", "")
            if q:
                query_to_nodes[q].append(node["id"])
        
        # Create links between nodes from the same query
        link_set = set()
        for query, node_ids in query_to_nodes.items():
            if len(node_ids) < 2:
                continue
            # Sort node_ids once to avoid sorting in the inner loop
            node_ids.sort()

            # Optimization: Use sequential linking (O(n)) instead of clique (O(n^2))
            # linking 0->1, 1->2, ... ensures connectivity without exploding edge count
            for i in range(len(node_ids) - 1):
                source = node_ids[i]
                target = node_ids[i+1]
                link_key = (source, target)
                if link_key not in link_set:
                    links.append({
                        "source": source,
                        "target": target,
                        "type": "same_query",
                        "value": 1
                    })
                    link_set.add(link_key)
        
        # Also link nodes from the same domain
        domain_to_nodes = defaultdict(list)
        for node in nodes:
            d = node.get("domain", "")
            if d:
                domain_to_nodes[d].append(node["id"])
        
        for domain, node_ids in domain_to_nodes.items():
            if len(node_ids) > 1 and len(node_ids) <= 20:  # Skip very common domains
                # Sort node_ids once to avoid sorting in the inner loop
                node_ids.sort()

                # Optimization: Use sequential linking here too
                for i in range(len(node_ids) - 1):
                    source = node_ids[i]
                    target = node_ids[i+1]
                    link_key = (source, target)
                    if link_key not in link_set:
                        links.append({
                            "source": source,
                            "target": target,
                            "type": "same_domain",
                            "value": 0.5
                        })
                        link_set.add(link_key)
        
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
