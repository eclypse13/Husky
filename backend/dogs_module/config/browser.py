# dogs_module/config/browser.py
"""Настройки Playwright-браузера."""

HEADLESS = True
TIMEOUT = 60_000  # 60 секунд
BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.1 Safari/605.1.15"
)

DELAY_BETWEEN_REQUESTS = (1.5, 3.0)  # (min, max) секунд
MAX_RETRIES = 3

# Обратная совместимость
PLAYWRIGHT_HEADLESS = HEADLESS
PLAYWRIGHT_TIMEOUT = TIMEOUT
PLAYWRIGHT_BROWSER_ARGS = BROWSER_ARGS
