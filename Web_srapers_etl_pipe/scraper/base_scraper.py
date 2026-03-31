# base class — subclasses implement platform-specific URL building and parsing

import asyncio
import random
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright

from scraper_utils import (
    try_again,
    get_log,
    mk_stealth,
    rnd_sleep,
    sv_json,
    slow_scroll,
    human_mouse_move,
    is_blocked,
    BROWSER_LAUNCH_ARGS,
)


def make_output_filename(platform: str, page_num: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{platform}_p{page_num}_{ts}.json"


class BaseScraper(ABC):
    platform: str = "unknown"

    def __init__(
        self,
        max_pages: int = 5,
        output_dir: Path = None,
        headless: bool = True,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        concurrency: int = 2,
        storage_state: Optional[Path] = None,
        save_storage_state: Optional[Path] = None,
    ):
        self.max_pages   = max_pages
        self.output_dir  = output_dir or Path(__file__).parent.parent / "run_outputs"
        self.headless    = headless
        self.min_delay   = min_delay
        self.max_delay   = max_delay
        self.concurrency = concurrency
        self.storage_state = Path(storage_state) if storage_state else None
        self.save_storage_state = Path(save_storage_state) if save_storage_state else None
        self.log         = get_log(self.__class__.__name__)

        if self.storage_state and not self.storage_state.exists():
            raise FileNotFoundError(f"storage state file not found: {self.storage_state}")

        # tracks platform::id combos so we don't write the same listing twice per run
        self.seen_keys: set[str] = set()

    @abstractmethod
    def build_url(self, page_num: int) -> str: pass

    @abstractmethod
    async def get_list_urls(self, search_page) -> list[str]: pass

    @abstractmethod
    async def get_details(self, detail_page, url: str) -> dict: pass

    async def _persist_storage_state(self, ctx) -> None:
        if not self.save_storage_state:
            return

        self.save_storage_state.parent.mkdir(parents=True, exist_ok=True)
        await ctx.storage_state(path=str(self.save_storage_state))
        self.storage_state = self.save_storage_state
        self.log.info(f"saved browser session to {self.save_storage_state}")

    async def prepare_session(self) -> None:
        if self.headless:
            raise ValueError("prepare_session requires a visible browser; use --no-headless")
        if not self.save_storage_state:
            raise ValueError("prepare_session requires --save-storage-state")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=BROWSER_LAUNCH_ARGS,
                slow_mo=random.randint(40, 90),
            )
            try:
                ctx = await mk_stealth(
                    browser,
                    headless=False,
                    storage_state=str(self.storage_state) if self.storage_state else None,
                )
                try:
                    page = await ctx.new_page()
                    await self._do_navigate(page, self.build_url(1))
                    print(
                        f"Solve any login or challenge for {self.platform} in the opened browser, "
                        "then return here."
                    )
                    await asyncio.to_thread(
                        input,
                        "Press Enter after the page is usable and you can see real content: ",
                    )
                    await self._persist_storage_state(ctx)
                finally:
                    await ctx.close()
            finally:
                await browser.close()

    async def scrape(self) -> list[dict]:
        self.log.info(f"starting scrape: {self.platform}, up to {self.max_pages} pages")
        all_listings = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=BROWSER_LAUNCH_ARGS,
                # slow_mo adds a bit of natural delay between Playwright actions
                slow_mo=random.randint(40, 90),
            )
            try:
                pg = 1
                while pg <= self.max_pages:
                    self.log.info(f"{self.platform} — page {pg}/{self.max_pages}")

                    page_rslt = await self._scrape_one_page(browser, pg)

                    if not page_rslt:
                        self.log.info("empty page — stopping early")
                        break

                    all_listings.extend(page_rslt)
                    self.log.info(f"page {pg} done: {len(page_rslt)} fresh listings")

                    out_f = self.output_dir / make_output_filename(self.platform, pg)
                    sv_json(page_rslt, out_f)

                    if pg < self.max_pages:
                        await rnd_sleep(self.min_delay, self.max_delay)

                    pg += 1
            finally:
                await browser.close()

        self.log.info(f"scrape complete — {len(all_listings)} total listings")
        return all_listings

    async def _do_navigate(self, page, url: str):
        # domcontentloaded is more reliable than networkidle on SPA sites
        # networkidle never fires on React/Next.js because they keep polling
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        # small random pause after dom ready — gives JS a moment to hydrate
        await rnd_sleep(1.0, 2.5)

    async def _scrape_one_page(self, browser, page_num: int) -> list[dict]:
        # fresh context per page — avoids cookies/session state bleeding between requests
        ctx = await mk_stealth(
            browser,
            self.headless,
            str(self.storage_state) if self.storage_state else None,
        )
        page_rslt = []

        try:
            search_url = self.build_url(page_num)

            srch_pg = None
            max_nav_tries = 3
            nav_attempt = 0
            while nav_attempt < max_nav_tries:
                nav_attempt += 1
                if srch_pg:
                    await srch_pg.close()
                srch_pg = await ctx.new_page()

                try:
                    await self._do_navigate(srch_pg, search_url)
                except Exception as nav_err:
                    self.log.warning(f"navigation error on attempt {nav_attempt}: {nav_err}")
                    if nav_attempt >= max_nav_tries:
                        break
                    await rnd_sleep(4.0, 8.0)
                    continue

                if await is_blocked(srch_pg):
                    # transient block — give it more time then retry with a fresh page
                    self.log.warning(f"search page {page_num} blocked (attempt {nav_attempt}) — waiting before retry")
                    if nav_attempt >= max_nav_tries:
                        self.log.warning(f"search page {page_num} still blocked after {max_nav_tries} attempts — skipping")
                        await srch_pg.close()
                        return page_rslt
                    await rnd_sleep(8.0 * nav_attempt, 15.0 * nav_attempt)
                    continue

                # page loaded and looks real — break out
                break

            if srch_pg is None:
                return page_rslt

            # mouse movement first, then scroll — hCaptcha watches for this sequence
            await human_mouse_move(srch_pg)
            await slow_scroll(srch_pg, steps=3)

            listing_urls = await self.get_list_urls(srch_pg)
            await srch_pg.close()

            if not listing_urls:
                return page_rslt

            sem = asyncio.Semaphore(self.concurrency)

            async def fetch_one(url: str):
                async with sem:
                    await rnd_sleep(self.min_delay, self.max_delay)
                    d_pg = await ctx.new_page()
                    try:
                        return await self.get_details(d_pg, url)
                    except Exception as err:
                        self.log.warning(f"failed to parse {url}: {err}")
                        return None
                    finally:
                        await d_pg.close()

            results = await asyncio.gather(*[fetch_one(u) for u in listing_urls])

            # print("debug:", [r.get("listing_id") if r else None for r in results])

            for listing in results:
                if listing is None:
                    continue
                dk = f"{listing.get('platform', '')}::{listing.get('listing_id', '')}"
                if listing.get("listing_id") and dk in self.seen_keys:
                    continue
                self.seen_keys.add(dk)
                page_rslt.append(listing)

            await self._persist_storage_state(ctx)

        finally:
            await ctx.close()

        return page_rslt
