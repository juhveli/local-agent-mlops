import time
from playwright.sync_api import sync_playwright

def verify_memory_view():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app
        page.goto("http://localhost:5173")

        # Wait for the app to load (look for "Agent Ops" in sidebar)
        page.wait_for_selector("text=Agent Ops")
        print("App loaded")

        # Click on "Memory Graph" button
        # The button has text "Memory Graph"
        page.click("text=Memory Graph")
        print("Clicked Memory Graph tab")

        # Wait for the MemoryView to load
        # In dev mode, it might be fast, or we might catch the loading state.
        # Let's wait for the header inside MemoryView: "Memory Graph"
        # Note: The sidebar button also says "Memory Graph".
        # The header has a database icon and "3D" badge.
        # Let's look for the text "Memory Graph" inside the main content area or the "3D" badge.
        # The badge: <span ...>3D</span>

        try:
            # Try to catch the loading state if possible, but don't fail if we miss it
            # The fallback text is "Loading 3D Graph..."
            loading = page.query_selector("text=Loading 3D Graph...")
            if loading:
                print("Saw loading state")
        except:
            pass

        # Wait for the actual component to render
        page.wait_for_selector("text=3D", timeout=10000)
        print("MemoryView loaded (saw '3D' badge)")

        # Take a screenshot
        page.screenshot(path="verification/memory_view.png")
        print("Screenshot saved")

        browser.close()

if __name__ == "__main__":
    verify_memory_view()
