import re
from playwright.sync_api import sync_playwright, expect

def test_memory_view_lazy_load(page):
    # Monitor network requests
    memory_chunk_requested = False

    def handle_request(request):
        nonlocal memory_chunk_requested
        if "MemoryView" in request.url and request.url.endswith(".js"):
            print(f"Request detected: {request.url}")
            memory_chunk_requested = True

    page.on("request", handle_request)

    print("Navigating to home...")
    page.goto("http://localhost:4173")

    # Ensure we are on Deep Research tab initially
    expect(page.get_by_text("Deep Research Agent")).to_be_visible()

    if memory_chunk_requested:
        print("FAILURE: MemoryView chunk requested before clicking tab!")
        exit(1)
    else:
        print("SUCCESS: MemoryView chunk NOT requested on initial load.")

    print("Clicking Memory Graph tab...")
    page.get_by_role("button", name="Memory Graph").click()

    # Wait for the chunk to be requested
    page.wait_for_timeout(2000) # Give it a moment

    if memory_chunk_requested:
        print("SUCCESS: MemoryView chunk requested after click.")
    else:
        print("FAILURE: MemoryView chunk NOT requested after click (or name changed).")
        # List requests that happened
        exit(1)

    # Take screenshot of the graph (or loader/error)
    # The graph might take time to render (WebGL), so we wait a bit more or look for canvas
    page.wait_for_timeout(3000)

    page.screenshot(path="verification/memory_view_loaded.png")
    print("Screenshot saved to verification/memory_view_loaded.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_memory_view_lazy_load(page)
        finally:
            browser.close()
