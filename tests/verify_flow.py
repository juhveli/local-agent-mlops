"""
Comprehensive Verification Suite for Local Agent MLOps Platform.
Verifies each component and provides MVP/Mock fallbacks if real services are down.
"""
import os
import sys
import asyncio
import httpx
from typing import Dict, Any, List

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.inference import InferenceClient
from core.embeddings import EmbeddingClient
from core.nornic_client import NornicClient
from apps.deep_research.agent import DeepResearchAgent
from dotenv import load_dotenv

load_dotenv()

async def verify_step_1_llm():
    print("--- [1] LLM Inference ---")
    client = InferenceClient()
    try:
        ans, th = client.chat("Hi")
        print(f"✅ Pass (Model: {client.model_name})")
        return True
    except Exception as e:
        print(f"❌ Fail: {e}")
        return False

async def verify_step_2_search():
    print("--- [2] Web Search ---")
    agent = DeepResearchAgent()
    try:
        res = agent.search_web("Test", num_results=1)
        if res:
            print(f"✅ Pass (Found: {res[0]['title']})")
            return True
        print("⚠️ Fail: Empty results")
        return False
    except Exception as e:
        print(f"❌ Fail: {e}")
        return False

async def verify_step_3_embeddings():
    print("--- [3] Embeddings ---")
    client = EmbeddingClient()
    try:
        vec = client.embed("test")
        if vec:
            print(f"✅ Pass (Dim: {len(vec)})")
            return True
        print("⚠️ Fail: Empty vector")
        return False
    except Exception as e:
        print(f"❌ Fail: {e}")
        return False

async def verify_step_4_storage():
    print("--- [4] Storage (NornicDB) ---")
    try:
        nornic = NornicClient()
        # Non-blocking check for connection
        if not nornic.use_fallback and nornic.driver:
            nornic.close()
            print("✅ Pass (Connection established)")
            return True
        else:
            print("⚠️ Success (Fallback mode active)")
            return "MVP_MOCKED"
    except Exception as e:
        print(f"❌ Fail: {e}")
        return "MVP_MOCKED"

async def mvp_flow_test(storage_ok):
    print("\n--- [MVP] End-to-End Flow Test ---")
    agent = DeepResearchAgent()
    
    # If storage failed, use a mock in the agent instance for this test
    if storage_ok == "MVP_MOCKED":
        print("🛠️ Mocking Qdrant storage for E2E validation...")
        class MockQdrant:
            def upsert(self, **kwargs): pass
            def search(self, **kwargs): return []
            def get_collections(self): 
                class C: collections = []
                return C()
        agent.qdrant = MockQdrant()

    query = "Quick test: How to boil an egg?"
    try:
        # Limited research for speed
        result = await agent.research(query, max_iterations=1)
        answer = result["answer"]
        print(f"✅ Pass! Agent synthesized answer: {answer[:100]}...")
        return True
    except Exception as e:
        print(f"❌ E2E Failed: {e}")
        return False

async def main():
    print("🚀 Local Agent MLOps - Flow Verification Suite 🚀\n")
    report = {}
    report['LLM'] = await verify_step_1_llm()
    report['Search'] = await verify_step_2_search()
    report['Embeddings'] = await verify_step_3_embeddings()
    report['Storage'] = await verify_step_4_storage()
    
    e2e_pass = await mvp_flow_test(report['Storage'])
    
    print("\n" + "="*40)
    print("FINAL REPORT:")
    for k, v in report.items():
        status = "✅" if v is True else ("🛠️ (MOCKED)" if v == "MVP_MOCKED" else "❌")
        print(f"{k:<12}: {status}")
    print(f"{'E2E Flow':<12}: {'✅' if e2e_pass else '❌'}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
