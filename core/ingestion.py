import os
import fitz  # pymupdf
import base64
import asyncio
from typing import List, Dict, Any
from core.inference import InferenceClient
from core.embeddings import get_embedding
from core.nornic_client import NornicClient
from core.observability import get_tracer
from opentelemetry import trace

tracer = get_tracer("ingestion")

class PDFIngestor:
    """
    Ingests PDF documents by converting pages to images, using a Vision LLM
    for extraction, and storing chunks in NornicDB.
    """

    def __init__(self):
        self.inference_client = InferenceClient()
        self.nornic_client = NornicClient()
        # Default to a generic name, user should configure this in .env or via LM Studio alias
        self.vision_model = os.getenv("VISION_MODEL_NAME", "qwen3-vl")

    @tracer.start_as_current_span("process_pdf")
    async def process(self, file_bytes: bytes, filename: str) -> int:
        """
        Process a PDF file and return the number of chunks ingested.
        Async method - leverages parallel inference requests.
        """
        span = trace.get_current_span()
        span.set_attribute("ingest.filename", filename)

        # 1. Convert PDF pages to images (CPU bound - run in thread)
        images_b64 = await asyncio.to_thread(self._pdf_to_images, file_bytes)
        span.set_attribute("ingest.page_count", len(images_b64))

        all_text = ""

        # 2. Extract content using Vision LLM
        # Optimization: Parallelize extraction to reduce total latency
        # With AsyncInferenceClient, we can fire off multiple requests
        tasks = [self._extract_content(img, i + 1) for i, img in enumerate(images_b64)]
        page_texts = await asyncio.gather(*tasks)

        for i, page_text in enumerate(page_texts):
            all_text += f"\n\n--- Page {i+1} ---\n\n{page_text}"

        # 3. Chunk text (CPU bound, fast enough to run in main thread or offload if very large)
        chunks = self._chunk_text(all_text)
        span.set_attribute("ingest.chunk_count", len(chunks))

        # 4. Embed and Store
        # Since upsert and embedding are sync network calls, we offload them to threads
        # We can also parallelize this if order doesn't strictly matter, but keeping order is nice for simple logic
        count = 0

        # Parallelize embedding generation and storage?
        # Maybe chunk them. For now, sequential async processing of chunks is safer/simpler.

        async def process_chunk(index, chunk_text):
            # Run get_embedding in thread
            embedding = await asyncio.to_thread(get_embedding, chunk_text)
            metadata = {
                "source": filename,
                "url": f"file://{filename}", # Virtual URL
                "chunk_index": index,
                "type": "pdf_ingestion"
            }
            # Use hash of content + filename as ID to allow re-ingestion updates
            # doc_id is handled in upsert_knowledge based on content hash usually, or passed in metadata?
            # NornicClient generates ID if not passed in metadata["id"]?
            # Let's pass ID in metadata to be safe and deterministic
            metadata["id"] = f"{filename}_{index}"

            # Run upsert in thread
            await asyncio.to_thread(self.nornic_client.upsert_knowledge, chunk_text, embedding, metadata)
            return 1

        # We can run chunk processing in parallel too
        chunk_tasks = [process_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*chunk_tasks)
        count = sum(results)

        return count

    def _pdf_to_images(self, file_bytes: bytes) -> List[str]:
        """Convert PDF bytes to list of base64 PNG strings."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=150) # Moderate DPI for balance of quality/size
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(img_b64)
        return images

    @tracer.start_as_current_span("vision_extract")
    async def _extract_content(self, image_b64: str, page_num: int) -> str:
        """Send image to Vision LLM to extract text."""
        prompt_content = [
            {
                "type": "text",
                "text": "Analyze this image of a document page. Extract all text content verbatim. Represent any tables using Markdown table syntax. Describe any important diagrams or images in detail. Do not add conversational filler."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }
            }
        ]

        try:
            # Async chat call
            content, _, _ = await self.inference_client.chat(
                prompt=prompt_content,
                system_prompt="You are a precise document digitization assistant.",
                model=self.vision_model
            )
            return content
        except Exception as e:
            print(f"Error extracting page {page_num}: {e}")
            return f"[Error extracting page {page_num}]"

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple recursive-like chunking strategy."""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:])
                break

            # Try to find a paragraph break
            last_newline = text.rfind('\n\n', start, end)
            if last_newline != -1 and last_newline > start + chunk_size * 0.5:
                end = last_newline
            else:
                # Try sentence break
                last_period = text.rfind('. ', start, end)
                if last_period != -1 and last_period > start + chunk_size * 0.5:
                    end = last_period + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks
