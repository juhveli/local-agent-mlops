"""
MCP Research Server - Tools for Deep Research Agent.
Provides search (SearXNG) and scrape capabilities.
"""
import os
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("ResearchServer")

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888")


@mcp.tool()
async def search_web(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Searches the web using SearXNG and returns a list of results.
    Each result contains 'title', 'url', and 'snippet'.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": query,
                "format": "json",
                "language": "fi-FI",
                "categories": "general",
            }
        )
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")
            })
        return results


@mcp.tool()
async def fetch_page_content(url: str) -> str:
    """
    Fetches and cleans content from a given URL.
    Returns plain text content suitable for LLM analysis.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove non-content elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
            
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        return text[:8000]  # Limit content size for LLM context


if __name__ == "__main__":
    mcp.run()
