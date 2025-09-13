from __future__ import annotations

import asyncio
import contextlib
import random
import sys
import time
from typing import Any, Final

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


# Минимум «обезличенных» эвристик для любого сайта
UA: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
LOCALE: Final[str] = "en-US"
GOTO_TIMEOUT_MS: Final[int] = 30000
NETIDLE_TIMEOUT_MS: Final[int] = 15000

BLOCK_MARKERS: Final[list[str]] = [
    "captcha",
    "cloudflare",
    "are you human",
    "request blocked",
    "verify you are human",
    "access denied",
    "attention required",
    "cf-chl",
    "cf-turnstile",
    "bot detection",
    "pardon the interruption",
    "429",
    "403",
]

# Пороговые значения для «страница парсабельна»
MIN_TEXT_LEN: Final[int] = 500  # видимый текст
MIN_LINKS: Final[int] = 8  # количество <a href>
MIN_DOM_NODES: Final[int] = 250  # размер DOM
MIN_IMAGES: Final[int] = 3  # <img> (часто индикатор контента)


async def _humanize(page: Page) -> None:
    await page.wait_for_timeout(int(random.uniform(250, 600)))
    # noinspection PyBroadException
    try:
        h = await page.evaluate(
            "() => Math.max(document.body.scrollHeight, "
            "document.documentElement.scrollHeight) || 2000"
        )
    except Exception:
        h = 2000
    for y in (0.25, 0.5, 0.75, 1.0):
        await page.mouse.wheel(0, h * y / 3.6)
        await page.wait_for_timeout(int(random.uniform(180, 360)))


async def _collect_metrics(page: Page) -> dict[str, Any]:
    js = """
    () => {
      const body = document.body || document.documentElement;
      const visibleText = (body.innerText || "").trim();
      const textLen = visibleText.length;

      const links = Array.from(document.querySelectorAll('a[href]'))
        .filter(a => {
          const href = (a.getAttribute('href') || '').trim();
          return href && !href.toLowerCase().startsWith('javascript:');
        });
      const images = document.querySelectorAll('img').length;
      const inputs = document.querySelectorAll('input, textarea, select, button').length;

      const domNodes = document.getElementsByTagName('*').length;

      // Некоторые сайты рендерят основной контент в <main> или крупные контейнеры
      const main = document.querySelector('main');
      const mainTextLen = main ? (main.textContent || "").trim().length : 0;

      const title = (document.title || "").trim();

      return {
        textLen, linksCount: links.length, images, inputs, domNodes, mainTextLen, title,
        htmlLower: document.documentElement.outerHTML.toLowerCase().slice(0, 200000)
      };
    }
    """
    return await page.evaluate(js)


def _looks_blocked(html_lower: str) -> bool:
    return any(m in html_lower for m in BLOCK_MARKERS)


def _is_parseable(m: dict[str, Any]) -> bool:
    # PASS, если страница выглядит «настоящей»: текст/ссылки/DOM/картинки — хотя бы по двум
    score = 0
    if m["textLen"] >= MIN_TEXT_LEN or m["mainTextLen"] >= MIN_TEXT_LEN // 2:
        score += 1
    if m["linksCount"] >= MIN_LINKS:
        score += 1
    if m["domNodes"] >= MIN_DOM_NODES:
        score += 1
    if m["images"] >= MIN_IMAGES:
        score += 1
    return score >= 2


async def _check_url(page: Page, url: str) -> tuple[bool, str]:
    t0 = time.perf_counter()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
    except Exception as e:
        return False, f"FAIL: navigation error: {e!r}"

    status = resp.status if resp else None
    if status and status >= 400:
        return False, f"FAIL: HTTP {status}"

    # noinspection PyBroadException
    with contextlib.suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=NETIDLE_TIMEOUT_MS)

    await _humanize(page)

    metrics = await _collect_metrics(page)
    html_lower = metrics.pop("htmlLower", "")

    if _looks_blocked(html_lower):
        return False, "FAIL: blocked/challenge markers present"

    t1 = time.perf_counter()
    parseable = _is_parseable(metrics)

    note = (
        f"text={metrics['textLen']}, links={metrics['linksCount']}, "
        f"imgs={metrics['images']}, dom={metrics['domNodes']}, "
        f"title='{metrics['title'][:80]}', t≈{t1 - t0:.1f}s"
    )
    if parseable:
        return True, f"PASS: {note}"
    else:
        return False, f"FAIL: weak content signal → {note}"


async def _run(urls: list[str]) -> int:
    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=True,
            args=[
                f"--user-agent={UA}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        # noinspection PyTypeChecker
        ctx: BrowserContext = await browser.new_context(
            user_agent=UA, locale=LOCALE, viewport={"width": 1280, "height": 900}
        )
        page: Page = await ctx.new_page()

        overall_ok = True
        try:
            for url in urls:
                ok, note = await _check_url(page, url)
                print(f"[{'OK' if ok else 'FAIL'}] {url} -> {note}")
                overall_ok &= ok
                await page.wait_for_timeout(int(random.uniform(500, 1000)))
        finally:
            await ctx.close()
            await browser.close()

    return 0 if overall_ok else 2


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python smoke.py <URL> [URL2 ...]")
        return 64
    return asyncio.run(_run(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
