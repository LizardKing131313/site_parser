from __future__ import annotations

import os
import random
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, suppress
from typing import Literal, TypedDict

from playwright.async_api import Browser, BrowserContext, Page, Request, Route, async_playwright


UserAgentKind = Literal["desktop", "mobile"]

UA_DESKTOP = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]
UA_MOBILE = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]

STEALTH_JS = r"""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = window.chrome || { runtime: {} };
const oq = window.navigator.permissions && window.navigator.permissions.query;
if (oq) {
  window.navigator.permissions.query = (p) =>
    p && p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : oq(p);
}
try { Object.defineProperty(Notification, 'permission', { get: () => 'default' }); } catch {}
try { Object.defineProperty(navigator, 'languages', { get: () => ['cs-CZ','cs','en-US','en'] }); } catch {}
try { Object.defineProperty(navigator, 'platform', { get: () => 'Win32' }); } catch {}
try {
  const gp = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel(R) UHD';
    return gp.call(this, param);
  };
} catch {}
"""  # noqa: E501


class ViewportSize(TypedDict):
    width: int
    height: int


DESKTOP_VIEWPORT: ViewportSize = {"width": 1280, "height": 900}
MOBILE_VIEWPORT: ViewportSize = {"width": 412, "height": 915}


def _rand_ua(kind: UserAgentKind) -> str:
    pool: Sequence[str] = UA_MOBILE if kind == "mobile" else UA_DESKTOP
    return random.choice(pool)


# noinspection PyUnusedLocal
@asynccontextmanager
async def fast_context(
    *,
    headful: bool | None = None,
    proxy: str | None = None,  # "http://user:pass@host:port" или "socks5://127.0.0.1:1080"
    locale: str = "cs-CZ",
    timezone_id: str = "Europe/Prague",
    ua_kind: UserAgentKind = "desktop",
    block_resources: bool = False,  # True → блок картинок/шрифтов/видео/трекеров
    navigation_timeout_ms: int = 30000,
    network_idle_timeout_ms: int = 20000,
) -> AsyncIterator[BrowserContext]:
    """
    Быстрый и устойчивый контекст Playwright.
    Использование:
        async with fast_context(...) as ctx:
            page = await ctx.new_page()
            ...
    """
    headful_env = os.getenv("HEADFUL", "")
    headful_val = (
        headful
        if headful is not None
        else (headful_env and headful_env not in ("0", "false", "False"))
    )
    proxy_env = os.getenv("PROXY_SERVER") or None
    proxy_final = proxy or proxy_env

    ua = _rand_ua(ua_kind)
    is_mobile = ua_kind == "mobile"
    viewport = MOBILE_VIEWPORT if is_mobile else DESKTOP_VIEWPORT
    dpr = 3 if is_mobile else 1

    async with async_playwright() as pw:
        launch_kwargs: dict = {
            "headless": not headful_val,
            "channel": "chrome",
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-features=IsolateOrigins,site-per-process",
                f"--user-agent={ua}",
            ],
        }
        if proxy_final:
            launch_kwargs["proxy"] = {"server": proxy_final}

        browser: Browser = await pw.chromium.launch(**launch_kwargs)
        ctx: BrowserContext = await browser.new_context(
            user_agent=ua,
            locale=locale,
            timezone_id=timezone_id,
            viewport=viewport,
            device_scale_factor=dpr,
            is_mobile=is_mobile,
            has_touch=is_mobile,
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept-Language": (
                    "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7" if locale == "cs-CZ" else "en-US,en;q=0.9"
                ),
                "Upgrade-Insecure-Requests": "1",
                "DNT": "1",
            },
        )

        await ctx.add_init_script(STEALTH_JS)
        ctx.set_default_navigation_timeout(navigation_timeout_ms)
        ctx.set_default_timeout(navigation_timeout_ms)

        if block_resources:

            async def _route(route: Route, request: Request) -> None:
                rtype: str = request.resource_type
                url: str = request.url
                if rtype in ("image", "media", "font") or any(
                    b in url for b in ("google-analytics.com", "gtm.js", "doubleclick.net")
                ):
                    await route.abort()
                else:
                    await route.continue_()

            await ctx.route("**/*", _route)

        try:
            yield ctx
        finally:
            await ctx.close()
            await browser.close()


async def quick_get(page: Page, url: str, *, wait_network_idle_ms: int = 20000) -> None:
    resp = await page.goto(url, wait_until="domcontentloaded")
    if resp and resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status} at {url}")
    with suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=wait_network_idle_ms)
