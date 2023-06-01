from typing import Dict

from playwright.async_api import Request, async_playwright
from playwright_stealth import stealth_async


class HttpHeadersManager:
    def __init__(self):
        self.headers_dict: Dict[str, Dict[str, str]] = {}

    async def get_headers(self, url: str) -> Dict[str, str]:
        def get_pw_headers(request: Request, url: str):
            if request.url == url:
                self.headers = request.headers

        if url not in self.headers_dict:
            async with async_playwright() as p:
                self.headers = {}
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()

                page = await context.new_page()
                await stealth_async(page)

                page.on(
                    "request",
                    lambda request: get_pw_headers(request, url),
                )
                await page.goto(url, wait_until="networkidle", timeout=15000)

                pw_cookies = await context.cookies()
                cookies_str = "; ".join(
                    [f"{cookie['name']}={cookie['value']}" for cookie in pw_cookies]
                )

                self.headers["cookie"] = cookies_str
                self.headers_dict[url] = self.headers

        return self.headers_dict[url]
