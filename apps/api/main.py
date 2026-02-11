import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from collections import defaultdict
from urllib.parse import urlparse
from pydantic import BaseModel

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.deep_research.agent import DeepResearchAgent
from apps.chat.agent import ChatAgent
from apps.api.models import ResearchRequest, ResearchResponse, ChatRequest, ChatResponse
from core.nornic_client import NornicClient
from core.ingestion import PDFIngestor
from core.inference import get_shared_inference_client

# TODO: Implement user authentication and session management.

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

# Deep Research Agent instance (shared to reuse clients)
deep_research_agent = DeepResearchAgent()

@app.post("/api/research", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    """
    Execute a deep research task and return the final answer.
    """
    try:
        # Use shared agent instance
        result = await deep_research_agent.research(
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

# Nornic client instance (shared for database connections)
nornic_client = NornicClient()

# PDF Ingestor instance
pdf_ingestor = PDFIngestor()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a PDF file using Vision LLM.
    Async to allow non-blocking ingestion (parallel requests to LLM server).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Check size (rough check via seek/tell if possible, or read chunks)
    # Using read() fits in memory since limit is 2.5MB
    MAX_SIZE = 2.5 * 1024 * 1024

    try:
        contents = await file.read()
        if len(contents) > MAX_SIZE:
             raise HTTPException(status_code=400, detail="File too large. Max 2.5MB.")

        # PDFIngestor.process is now async
        chunk_count = await pdf_ingestor.process(contents, file.filename)
        return {"status": "ok", "message": f"Ingested {file.filename}", "chunks": chunk_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the GraphRAG chat agent.
    """
    try:
        # ChatAgent.chat is now async
        response = await chat_agent.chat(request.message)

        # Retrieve context asynchronously to avoid blocking
        # Note: This duplicates work done inside chat_agent, but we need the count here
        # Optimization: In future, refactor ChatAgent.chat to return metadata
        context_docs = await asyncio.to_thread(chat_agent._retrieve_context, request.message, limit=3)

        return ChatResponse(
            message=response,
            sources_used=len(context_docs)
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

class UnloadRequest(BaseModel):
    model_name: str = None

@app.post("/api/models/unload")
async def unload_model(request: UnloadRequest = Body(default=None)):
    """
    Trigger model offloading in LM Studio server to free VRAM.
    Useful when the app enters idle state.
    """
    client = get_shared_inference_client()
    model = request.model_name if request else None
    success = await client.unload_model(model)
    if success:
        return {"status": "ok", "message": "Model unloaded"}
    else:
        raise HTTPException(status_code=500, detail="Failed to unload model")


@app.get("/api/memory/graph")
async def get_memory_graph():
    """
    Fetch knowledge graph data for visualization.
    Returns nodes and links from NornicDB.
    """
    try:
        # Wrap the entire synchronous logic in a thread to be non-blocking
        return await asyncio.to_thread(_get_memory_graph_sync)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _get_memory_graph_sync():
    """
    Synchronous implementation of get_memory_graph logic.
    """
    nodes = []
    links = []

    if nornic_client.use_fallback:
        # Fallback: Load from JSON file
        import json
        if os.path.exists(nornic_client.fallback_file):
            with open(nornic_client.fallback_file, "r") as f:
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
        with nornic_client.driver.session() as session:
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
    research_collection = "research_knowledge_v2"

    if nornic_client.qdrant and not nornic_client.use_fallback:
        try:
            scroll_result = nornic_client.qdrant.scroll(
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
        node_ids.sort()
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
        if len(node_ids) > 1 and len(node_ids) <= 20:
            node_ids.sort()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
