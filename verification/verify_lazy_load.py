from playwright.sync_api import sync_playwright, expect

def verify_lazy_load(page):
    print("Navigating to app...")
    page.goto("http://localhost:5173")

    # Wait for Deep Research (default tab)
    print("Checking default tab...")
    expect(page.get_by_role("heading", name="Deep Research Agent")).to_be_visible()
    page.screenshot(path="verification/1_research_view.png")

    # Click Memory Graph
    print("Clicking Memory Graph...")
    page.get_by_role("button", name="Memory Graph").click()

    # Expect Memory View to load (it might fail to fetch data, but the header should appear)
    # The header has "Memory Graph" text
    print("Waiting for Memory Graph header...")
    expect(page.get_by_role("heading", name="Memory Graph")).to_be_visible()

    # Take screenshot
    page.screenshot(path="verification/2_memory_view.png")
    print("Screenshots saved.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_lazy_load(page)
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()
