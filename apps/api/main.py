import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.deep_research.agent import DeepResearchAgent
from apps.api.models import ResearchRequest, ResearchResponse

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
