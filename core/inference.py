import os
import re
from typing import Optional, Tuple
from openai import OpenAI
from opentelemetry import trace
from dotenv import load_dotenv
from core.observability import get_tracer

load_dotenv()
tracer = get_tracer("inference")

class InferenceClient:
    """
    Client for interacting with LM Studio via OpenAI SDK.
    Supports extract 'thinking' blocks from Qwen models.
    """
    
    def __init__(self, base_url: str = None, api_key: str = "lm-studio"):
        self.base_url = base_url or os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.client = OpenAI(base_url=self.base_url, api_key=api_key)
        self.model_name = os.getenv("MODEL_NAME", "qwen3-30b-a3b-thinking-2507-mlx")

    @tracer.start_as_current_span("llm_completion")
    def chat(self, prompt: str, system_prompt: str = "You are a helpful research assistant.") -> Tuple[str, Optional[str]]:
        """
        Sends a chat completion request and returns (clean_answer, thought).
        """
        span = trace.get_current_span()
        span.set_attribute("llm.model", self.model_name)
        span.set_attribute("llm.prompt", prompt)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0 # Keeping it deterministic for research
        )

        content = response.choices[0].message.content
        thought = None

        # Check for reasoning_content (some providers/models use this field)
        if hasattr(response.choices[0].message, 'reasoning_content'):
            thought = response.choices[0].message.reasoning_content
        
        # Fallback: Parse <thought> tags if embedded in content
        if not thought:
            thought_match = re.search(r'<thought>(.*?)</thought>', content, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
                content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()

        span.set_attribute("llm.answer", content)
        if thought:
            span.set_attribute("llm.thought", thought)
            
        return content, thought

if __name__ == "__main__":
    from core.observability import init_observability
    from opentelemetry import trace
    
    init_observability()
    client = InferenceClient()
    print(f"Testing {client.model_name}...")
    try:
        answer, thought = client.chat("Explain the concept of GraphRAG in one sentence.")
        print(f"\n[Thought]: {thought[:100] if thought else 'None'}...")
        print(f"[Answer]: {answer}")
    except Exception as e:
        print(f"Error: {e}")
