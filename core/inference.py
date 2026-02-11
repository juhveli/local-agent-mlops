import os
import re
import httpx
from typing import Optional, Tuple, Union, List, Dict, Any
from openai import AsyncOpenAI
from opentelemetry import trace
from dotenv import load_dotenv
from core.observability import get_tracer

load_dotenv()
tracer = get_tracer("inference")

class InferenceClient:
    """
    Async Client for interacting with LM Studio via OpenAI SDK.
    Supports extract 'thinking' blocks from Qwen models.
    """
    
    def __init__(self, base_url: str = None, api_key: str = "lm-studio"):
        self.base_url = base_url or os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        # Use AsyncOpenAI for non-blocking I/O
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=api_key)
        self.model_name = os.getenv("MODEL_NAME", "qwen3-30b-a3b-thinking-2507-mlx")

    @tracer.start_as_current_span("llm_completion")
    async def chat(
        self,
        prompt: Union[str, List[Dict]],
        system_prompt: str = "You are a helpful research assistant.",
        model: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        stream_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Sends a chat completion request and returns (clean_answer, thought, response_id).

        Args:
            prompt: User input string or list of content parts (for multimodal).
            system_prompt: System instruction.
            model: Optional override for model name.
            previous_response_id: ID of the previous response for stateful context.
            stream_options: Options for streaming (e.g. {"include_usage": True}).
        """
        span = trace.get_current_span()
        used_model = model or self.model_name
        span.set_attribute("llm.model", used_model)

        if isinstance(prompt, str):
            span.set_attribute("llm.prompt", prompt)
        else:
            span.set_attribute("llm.prompt", "multimodal_content")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        # LM Studio 0.4.0 supports stateful context via previous_response_id
        extra_body = {}
        if previous_response_id:
            extra_body["previous_response_id"] = previous_response_id
            span.set_attribute("llm.previous_response_id", previous_response_id)

        # Standard parameters
        params = {
            "model": used_model,
            "messages": messages,
            "temperature": 0.0, # Deterministic
            "extra_body": extra_body
        }
        
        if stream_options:
             params["stream"] = True
             params["stream_options"] = stream_options

        try:
            response = await self.client.chat.completions.create(**params)
        except Exception as e:
            # tracing error
            span.record_exception(e)
            raise e

        # Handle non-streaming response
        if not params.get("stream"):
            content = response.choices[0].message.content
            response_id = response.id
            thought = None

            # Check for reasoning_content
            if hasattr(response.choices[0].message, 'reasoning_content'):
                thought = response.choices[0].message.reasoning_content

            # Fallback: Parse <thought> tags
            if not thought and content:
                thought_match = re.search(r'<thought>(.*?)</thought>', content, re.DOTALL | re.IGNORECASE)
                if thought_match:
                    thought = thought_match.group(1).strip()
                    content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()

            span.set_attribute("llm.answer", content or "")
            if thought:
                span.set_attribute("llm.thought", thought)

            return content, thought, response_id
        else:
            # TODO: Implement full streaming handling if needed.
            # For now, we assume non-streaming usage in this method signature or throw error.
            # But the requirement asked to set stream: true.
            # If we set stream=True, 'response' is an AsyncStream.
            # We need to consume it to get content.

            full_content = ""
            full_thought = ""
            current_response_id = None

            async for chunk in response:
                current_response_id = chunk.id
                if chunk.choices and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content
                # Handle streaming thought if supported (e.g. via specific delta field)
                # Currently standard OpenAI chunk delta doesn't have reasoning_content standardly yet,
                # but DeepSeek/others might use it.
                # For now, we just accumulate content.

            # Post-process thought tags from full content
            thought = None
            thought_match = re.search(r'<thought>(.*?)</thought>', full_content, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
                full_content = re.sub(r'<thought>.*?</thought>', '', full_content, flags=re.DOTALL | re.IGNORECASE).strip()
            
            return full_content, thought, current_response_id

    async def unload_model(self, model_name: str = None):
        """
        Unloads a model to free VRAM.
        Uses the LM Studio API endpoint: POST /api/v1/models/unload
        """
        target_model = model_name or self.model_name
        # The endpoint might be /v1/models/unload or /api/v1/models/unload depending on server version.
        # Based on prompt: "POST /api/v1/models/unload"

        # We need to construct the URL manually since OpenAI client doesn't support this custom endpoint directly easily?
        # Actually we can use httpx.

        url = f"{self.base_url.replace('/v1', '')}/api/v1/models/unload"
        # If base_url is http://localhost:1234/v1, we want http://localhost:1234/api/v1/models/unload

        async with httpx.AsyncClient() as client:
            try:
                # We might need to handle the case where base_url doesn't end in /v1
                base = self.base_url.rstrip("/")
                if base.endswith("/v1"):
                     base = base[:-3]

                # Try the documented endpoint
                resp = await client.post(f"{base}/api/v1/models/unload", json={"model": target_model})
                # If 404, maybe it's just /v1/models/unload?
                if resp.status_code == 404:
                     resp = await client.post(f"{base}/v1/models/unload", json={"model": target_model})

                return resp.status_code == 200
            except Exception as e:
                print(f"Error unloading model: {e}")
                return False


_SHARED_CLIENT: Optional['InferenceClient'] = None

def get_shared_inference_client() -> 'InferenceClient':
    """
    Returns a singleton instance of Async InferenceClient.
    """
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        _SHARED_CLIENT = InferenceClient()
    return _SHARED_CLIENT


async def generate_response(messages: list, temperature: float = 0.0, previous_response_id: str = None) -> Tuple[str, str]:
    """
    Simplified helper for chat completion with a list of messages.
    Returns (content, response_id).
    """
    client = get_shared_inference_client()

    # Extract system prompt if present
    system_prompt = "You are a helpful assistant."
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        else:
            user_messages.append(msg)

    # For multi-turn, we use the raw client to handle the message list properly
    # BUT, we want to support previous_response_id

    # We can use the client.chat method if we reconstruct the prompt, but generate_response accepts full history.
    # So we use client.client directly.

    all_messages = [{"role": "system", "content": system_prompt}] + user_messages

    extra_body = {}
    if previous_response_id:
        extra_body["previous_response_id"] = previous_response_id

    response = await client.client.chat.completions.create(
        model=client.model_name,
        messages=all_messages,
        temperature=temperature,
        extra_body=extra_body
    )

    return response.choices[0].message.content, response.id

if __name__ == "__main__":
    import asyncio
    from core.observability import init_observability
    
    init_observability()

    async def test():
        client = InferenceClient()
        print(f"Testing {client.model_name}...")
        try:
            answer, thought, rid = await client.chat("Explain the concept of GraphRAG in one sentence.")
            print(f"\n[Thought]: {thought[:100] if thought else 'None'}...")
            print(f"[Answer]: {answer}")
            print(f"[ID]: {rid}")
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
