from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Navigate to the app
    page.goto("http://localhost:8501")

    # Take a screenshot of the initial page for debugging
    page.screenshot(path="jules-scratch/verification/00_initial_view.png")

    # Wait for the main title to be visible, with an increased timeout
    try:
        expect(page.locator('h1:has-text("🏠 Inicio")')).to_be_visible(timeout=10000)
    except Exception as e:
        page.screenshot(path="jules-scratch/verification/00_error_view.png")
        print(f"Error waiting for main title: {e}")
        # Re-raise the exception to fail the test
        raise

    # Take a screenshot of the "Inicio" page
    page.screenshot(path="jules-scratch/verification/01_inicio_page.png")

    # Navigate to the "Tareas" page by finding a link in the sidebar
    # The links are within a div with a specific data-testid
    sidebar = page.locator('[data-testid="stSidebarNav"]')
    sidebar.get_by_role("link", name="✅ Tareas").click()

    # Wait for the "Tareas" title to be visible
    expect(page.locator('h1:has-text("📋 Tareas")')).to_be_visible()

    # Take a screenshot of the "Tareas" page
    page.screenshot(path="jules-scratch/verification/02_tareas_page.png")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)