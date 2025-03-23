from playwright.sync_api import sync_playwright

def start_browser():
    playwright = sync_playwright().start()
    browser = playwright.webkit.launch()
    return playwright, browser

def close_browser(playwright, browser):
    if browser:
        browser.close()
    if playwright:
        playwright.stop()