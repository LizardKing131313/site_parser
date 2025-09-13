from __future__ import annotations

import asyncio
import json
import random
import sys
from dataclasses import asdict, dataclass
from typing import Final

from .playwright_fast import UA_DESKTOP, UA_MOBILE, UserAgentKind, fast_context, quick_get


UA_POOL: Final[list[str]] = UA_DESKTOP + UA_MOBILE
LOCALES: Final[list[str]] = ["cs-CZ", "en-US"]
TIMEZONES: Final[list[str]] = ["Europe/Prague", "UTC"]

# Сколько профилей максимум пробовать
MAX_PROFILES: Final[int] = 12


@dataclass
class Profile:
    user_agent: str
    ua_kind: UserAgentKind
    locale: str
    timezone_id: str
    block_resources: bool
    network_idle_timeout_ms: int


def _rand_profiles() -> list[Profile]:
    profiles: list[Profile] = []
    ua_pool = UA_POOL[:]
    random.shuffle(ua_pool)

    for ua in ua_pool:
        ua_kind: UserAgentKind = "mobile" if "Android" in ua else "desktop"
        for loc in LOCALES:
            for tz in TIMEZONES:
                for netidle in (25000, 15000):
                    for block in (True, False):
                        p = Profile(
                            user_agent=ua,
                            ua_kind=ua_kind,
                            locale=loc,
                            timezone_id=tz,
                            block_resources=block,
                            network_idle_timeout_ms=netidle,
                        )
                        profiles.append(p)
    random.shuffle(profiles)
    return profiles[:MAX_PROFILES]


async def _try_profile(urls: list[str], p: Profile) -> tuple[bool, list[str]]:
    notes: list[str] = []
    async with fast_context(
        ua_kind=p.ua_kind,
        locale=p.locale,
        timezone_id=p.timezone_id,
        block_resources=p.block_resources,
    ) as ctx:
        page = await ctx.new_page()
        overall = True
        try:
            for url in urls:
                try:
                    await quick_get(page, url, wait_network_idle_ms=p.network_idle_timeout_ms)
                    notes.append(f"[OK] {url}")
                except Exception as e:
                    notes.append(f"[FAIL] {url} -> {e}")
                    overall = False
        finally:
            await page.close()
    return overall, notes


async def _run(urls: list[str]) -> int:
    profiles = _rand_profiles()
    for attempt, p in enumerate(profiles, start=1):
        print(f"=== Attempt {attempt}/{len(profiles)} ===")
        ok, notes = await _try_profile(urls, p)
        for line in notes:
            print(line)

        if ok:
            print("\nWORKING PROFILE:")
            print(json.dumps(asdict(p), ensure_ascii=False, indent=2))
            return 0

        print("Profile failed, trying next...\n")
    print("No working profile found within limits.")
    return 2


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python smoke.py <URL> [URL2 ...]")
        return 64
    urls = sys.argv[1:]
    return asyncio.run(_run(urls))


if __name__ == "__main__":
    raise SystemExit(main())
