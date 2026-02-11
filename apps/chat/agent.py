"""
GraphRAG Chat Agent - Knowledge-grounded conversational AI.
"""
import os
import sys
import asyncio
from typing import List, Dict, Any
from opentelemetry import trace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.observability import get_tracer
from core.inference import generate_response
from core.embeddings import get_embedding
from core.nornic_client import NornicClient

tracer = get_tracer("chat_agent")

class ChatAgent:
    """
    A conversational agent that grounds responses in knowledge from NornicDB.
    """

    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.last_response_id: str = None
        self.nornic = NornicClient()
        self.system_prompt = """You are a helpful AI assistant with access to a knowledge base.
When answering questions, use the provided context from the knowledge base when relevant.
If the context doesn't contain relevant information, you may use your general knowledge but indicate this.
Be concise and helpful. Format responses in Markdown when appropriate."""

    @tracer.start_as_current_span("chat_retrieve_context")
    def _retrieve_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from NornicDB based on the query. Blocking."""
        span = trace.get_current_span()
        span.set_attribute("chat.query", query)

        if self.nornic.use_fallback:
            # Fallback: load from JSON file
            import json
            if os.path.exists(self.nornic.fallback_file):
                with open(self.nornic.fallback_file, "r") as f:
                    data = json.load(f)
                return data[:limit]
            return []

        # Embed query and search
        # Note: get_embedding is sync (network I/O), running in thread via parent call
        query_vector = get_embedding(query)
        results = self.nornic.hybrid_search(query_vector, limit=limit)

        span.set_attribute("chat.retrieved_count", len(results))
        return results

    @tracer.start_as_current_span("chat_generate")
    async def chat(self, user_message: str) -> str:
        """
        Process a user message and return an AI response.
        """
        span = trace.get_current_span()
        span.set_attribute("chat.user_message", user_message[:200])
        
        # 1. Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # 2. Retrieve relevant context (Run in thread to avoid blocking)
        context_docs = await asyncio.to_thread(self._retrieve_context, user_message)
        
        # 3. Build context string
        context_str = ""
        if context_docs:
            context_str = "\n\n---\n**Knowledge Base Context:**\n"
            for i, doc in enumerate(context_docs, 1):
                content = doc.get("content", "")[:500]
                url = doc.get("url", doc.get("metadata", {}).get("url", ""))
                context_str += f"\n[{i}] {content}"
                if url:
                    context_str += f"\n   Source: {url}"
            context_str += "\n---\n"
        
        # 4. Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt + context_str}]
        
        # Include last N turns of conversation for memory
        history_window = self.conversation_history[-10:]  # Keep last 10 messages
        for msg in history_window:
            messages.append(msg)
        
        # 5. Generate response
        response_content, response_id = await generate_response(
            messages,
            previous_response_id=self.last_response_id
        )
        
        # Update state
        if response_id:
            self.last_response_id = response_id

        # 6. Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response_content})
        
        span.set_attribute("chat.response_length", len(response_content))
        return response_content

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.last_response_id = None


if __name__ == "__main__":
    # Test the chat agent
    from core.observability import init_observability
    init_observability()

    async def main():
        agent = ChatAgent()
        print("ChatAgent initialized. Type 'quit' to exit.\n")
        while True:
            # simple input loop (blocking input, but okay for test script)
            user_input = input("You: ")
            if user_input.lower() == "quit":
                break
            response = await agent.chat(user_input)
            print(f"\nAssistant: {response}\n")

    asyncio.run(main())
