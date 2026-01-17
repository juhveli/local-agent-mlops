import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

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
                    if not any(n["id"] == node_id for n in nodes):
                        nodes.append({
                            "id": node_id,
                            "name": payload.get("url", f"Vector {node_id}")[:50],
                            "content": payload.get("content", "")[:200],
                            "group": 2  # Different group for vector-only nodes
                        })
            except Exception:
                pass  # Qdrant might not have data yet
        
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
