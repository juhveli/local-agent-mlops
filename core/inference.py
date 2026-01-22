import os
import re
from typing import Optional, Tuple, Union, List, Dict
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
    def chat(self, prompt: Union[str, List[Dict]], system_prompt: str = "You are a helpful research assistant.", model: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Sends a chat completion request and returns (clean_answer, thought).

        Args:
            prompt: User input string or list of content parts (for multimodal).
            system_prompt: System instruction.
            model: Optional override for model name (e.g. for vision tasks).
        """
        span = trace.get_current_span()
        used_model = model or self.model_name
        span.set_attribute("llm.model", used_model)

        if isinstance(prompt, str):
            span.set_attribute("llm.prompt", prompt)
        else:
            span.set_attribute("llm.prompt", "multimodal_content")

        response = self.client.chat.completions.create(
            model=used_model,
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


def generate_response(messages: list, temperature: float = 0.0) -> str:
    """
    Simplified helper for chat completion with a list of messages.
    Returns only the content (no thought extraction).
    """
    client = InferenceClient()

    # Extract system prompt if present
    system_prompt = "You are a helpful assistant."
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            user_messages.append(msg)

    # For multi-turn, we need to use the raw client
    all_messages = [{"role": "system", "content": system_prompt}] + user_messages

    response = client.client.chat.completions.create(
        model=client.model_name,
        messages=all_messages,
        temperature=temperature
    )

    return response.choices[0].message.content

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
