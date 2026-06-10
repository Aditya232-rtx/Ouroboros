"""
Ouroboros Red Agent - Browser Tool
Ported from Strix Browser Instance.
Provides Headless Chrome capabilities for DOM-based testing (XSS/Crawling).
"""

import asyncio
import base64
import contextlib
import logging
import threading
from typing import Any, cast, Dict, Optional

# Try to import playwright, but don't fail if missing (optional dependency)
try:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
except ImportError:
    Browser = Any
    BrowserContext = Any
    Page = Any
    Playwright = Any
    async_playwright = None

logger = logging.getLogger(__name__)

MAX_PAGE_SOURCE_LENGTH = 20_000
MAX_CONSOLE_LOG_LENGTH = 30_000
MAX_INDIVIDUAL_LOG_LENGTH = 1_000
MAX_CONSOLE_LOGS_COUNT = 200

class _BrowserState:
    """Singleton state for the shared browser instance."""
    lock = threading.Lock()
    event_loop: asyncio.AbstractEventLoop | None = None
    event_loop_thread: threading.Thread | None = None
    playwright: Playwright | None = None
    browser: Browser | None = None

_state = _BrowserState()

def _ensure_event_loop() -> None:
    if _state.event_loop is not None:
        return

    def run_loop() -> None:
        _state.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_state.event_loop)
        _state.event_loop.run_forever()

    _state.event_loop_thread = threading.Thread(target=run_loop, daemon=True)
    _state.event_loop_thread.start()

    while _state.event_loop is None:
        threading.Event().wait(0.01)

async def _create_browser() -> Browser:
    if not async_playwright:
        raise ImportError("Playwright not installed. Run 'pip install playwright && playwright install chromium'")

    if _state.browser is not None and _state.browser.is_connected():
        return _state.browser

    if _state.browser is not None:
        with contextlib.suppress(Exception):
            await _state.browser.close()
        _state.browser = None
    if _state.playwright is not None:
        with contextlib.suppress(Exception):
            await _state.playwright.stop()
        _state.playwright = None

    _state.playwright = await async_playwright().start()
    _state.browser = await _state.playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
        ],
    )
    return _state.browser

def _get_browser() -> tuple[asyncio.AbstractEventLoop, Browser]:
    with _state.lock:
        _ensure_event_loop()
        if _state.browser is None or not _state.browser.is_connected():
            future = asyncio.run_coroutine_threadsafe(_create_browser(), _state.event_loop)
            future.result(timeout=30)
        return _state.event_loop, _state.browser

class BrowserTool:
    """
    Browser Tool for Authorization & Web Testing.
    Consolidated from Strix's BrowserInstance.
    """
    def __init__(self) -> None:
        self.is_running = True
        self._execution_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.pages: Dict[str, Page] = {}
        self.current_page_id: str | None = None
        self._next_tab_id = 1
        self.console_logs: Dict[str, list[dict[str, Any]]] = {}

    def _run_async(self, coro: Any) -> Dict[str, Any]:
        if not self._loop or not self.is_running:
            raise RuntimeError("Browser instance is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return cast("dict[str, Any]", future.result(timeout=30))

    async def _create_context(self, url: str | None = None) -> Dict[str, Any]:
        self.context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await self.context.new_page()
        tab_id = f"tab_{self._next_tab_id}"
        self._next_tab_id += 1
        self.pages[tab_id] = page
        self.current_page_id = tab_id
        
        if url:
            await page.goto(url, wait_until="domcontentloaded")
            
        return await self._get_page_state(tab_id)

    async def _get_page_state(self, tab_id: str) -> Dict[str, Any]:
        page = self.pages[tab_id]
        # Wait for potential rendering
        await asyncio.sleep(1)
        
        screenshot_bytes = await page.screenshot(type="png", full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        return {
            "screenshot": screenshot_b64,
            "url": page.url,
            "title": await page.title(),
            "source": (await page.content())[:MAX_PAGE_SOURCE_LENGTH],
            "tab_id": tab_id
        }

    def launch(self, url: str | None = None) -> Dict[str, Any]:
        with self._execution_lock:
            if self.context is not None:
                return {"error": "Browser already launched"}
            self._loop, self._browser = _get_browser()
            return self._run_async(self._create_context(url))

    def goto(self, url: str) -> Dict[str, Any]:
        with self._execution_lock:
            return self._run_async(self._goto(url))

    async def _goto(self, url: str) -> Dict[str, Any]:
        if not self.current_page_id:
            raise ValueError("No active tab")
        await self.pages[self.current_page_id].goto(url, wait_until="domcontentloaded")
        return await self._get_page_state(self.current_page_id)
    
    def close(self):
        with self._execution_lock:
            self.is_running = False
            self.pages.clear()
            self.context = None
