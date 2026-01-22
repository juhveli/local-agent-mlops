import os
import fitz  # pymupdf
import base64
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
    def process(self, file_bytes: bytes, filename: str) -> int:
        """
        Process a PDF file and return the number of chunks ingested.
        Blocking method - run in threadpool if calling from async context.
        """
        span = trace.get_current_span()
        span.set_attribute("ingest.filename", filename)

        # 1. Convert PDF pages to images
        images_b64 = self._pdf_to_images(file_bytes)
        span.set_attribute("ingest.page_count", len(images_b64))

        all_text = ""

        # 2. Extract content using Vision LLM
        # TODO: Parallelize this for performance if needed
        for i, img_b64 in enumerate(images_b64):
            page_text = self._extract_content(img_b64, i + 1)
            all_text += f"\n\n--- Page {i+1} ---\n\n{page_text}"

        # 3. Chunk text
        chunks = self._chunk_text(all_text)
        span.set_attribute("ingest.chunk_count", len(chunks))

        # 4. Embed and Store
        count = 0
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            metadata = {
                "source": filename,
                "url": f"file://{filename}", # Virtual URL
                "chunk_index": i,
                "type": "pdf_ingestion"
            }
            # Use hash of content + filename as ID to allow re-ingestion updates
            doc_id = f"{filename}_{i}"

            self.nornic_client.upsert_knowledge(chunk, embedding, metadata)
            count += 1

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
    def _extract_content(self, image_b64: str, page_num: int) -> str:
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
            content, _ = self.inference_client.chat(
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
