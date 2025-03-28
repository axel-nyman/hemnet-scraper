from playwright.sync_api import sync_playwright
import random
from contextlib import contextmanager

# List of common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

@contextmanager
def browser_context():
    """Context manager for browser handling that ensures proper cleanup"""
    playwright = None
    browser = None
    try:
        playwright = sync_playwright().start()
        browser = playwright.webkit.launch(headless=True)
        yield playwright, browser
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

@contextmanager
def page_context(browser):
    """Context manager for page handling that ensures proper cleanup"""
    user_agent = get_random_user_agent()
    context = browser.new_context(user_agent=user_agent)
    page = context.new_page()
    try:
        yield page
    finally:
        page.close()
        context.close()