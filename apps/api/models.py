from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ResearchRequest(BaseModel):
    query: str
    max_iterations: int = 3
    provider: str = "tavily"
    search_depth: str = "basic"
    include_domains: List[str] = []

class Source(BaseModel):
    id: int
    url: str
    title: str
    content: str
    query: str

class ResearchResponse(BaseModel):
    answer: str
    sources: List[Source]
    trace_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    sources_used: int = 0
