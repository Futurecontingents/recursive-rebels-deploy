from typing import Optional

from playwright.async_api import Page

from base_scraper import BaseScraper
from propertyfinder.constants import NEXT_DATA_SELECTOR
from propertyfinder.parser import (
    build_search_url,
    extract_search_result,
    parse_next_data,
    records_from_search_result,
)
from scraper_utils import get_log, human_mouse_move, is_blocked, mk_stealth, rnd_sleep, slow_scroll

log = get_log("PropertyFinder")


class PropertyFinderScraper(BaseScraper):
    platform = "propertyfinder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._record_cache: dict[str, dict] = {}

    def build_url(self, page_num: int) -> str:
        return build_search_url(page_num)

    async def _scrape_one_page(self, browser, page_num: int) -> list[dict]:
        ctx = await mk_stealth(
            browser,
            self.headless,
            str(self.storage_state) if self.storage_state else None,
        )
        page_records: list[dict] = []

        try:
            search_url = self.build_url(page_num)
            search_page = None
            max_nav_tries = 3

            for nav_attempt in range(1, max_nav_tries + 1):
                if search_page is not None:
                    await search_page.close()
                search_page = await ctx.new_page()

                try:
                    await self._do_navigate(search_page, search_url)
                except Exception as nav_err:
                    log.warning(f"propertyfinder navigation error on attempt {nav_attempt}: {nav_err}")
                    if nav_attempt >= max_nav_tries:
                        break
                    await rnd_sleep(4.0, 8.0)
                    continue

                if await is_blocked(search_page):
                    log.warning(
                        f"propertyfinder search page {page_num} blocked "
                        f"(attempt {nav_attempt})"
                    )
                    if nav_attempt >= max_nav_tries:
                        await search_page.close()
                        return page_records
                    await rnd_sleep(8.0 * nav_attempt, 15.0 * nav_attempt)
                    continue

                break

            if search_page is None:
                return page_records

            await human_mouse_move(search_page)
            await slow_scroll(search_page, steps=3)
            listing_urls = await self.get_list_urls(search_page)
            await search_page.close()

            for listing_url in listing_urls:
                record = self._record_cache.pop(listing_url, None)
                if record is None:
                    continue

                dedupe_key = f"{record.get('platform', '')}::{record.get('listing_id', '')}"
                if record.get("listing_id") and dedupe_key in self.seen_keys:
                    continue

                self.seen_keys.add(dedupe_key)
                page_records.append(record)

            await self._persist_storage_state(ctx)
        finally:
            await ctx.close()

        return page_records

    async def get_list_urls(self, search_page: Page) -> list[str]:
        await search_page.wait_for_selector(
            NEXT_DATA_SELECTOR,
            state="attached",
            timeout=25_000,
        )
        raw_payload = await search_page.text_content(NEXT_DATA_SELECTOR)
        next_data = parse_next_data(raw_payload or "")
        search_result = extract_search_result(next_data)
        search_url = build_search_url(search_result.get("meta", {}).get("page") or 1)

        urls: list[str] = []
        seen_urls: set[str] = set()
        self._record_cache = {}

        for record in records_from_search_result(search_result, search_url=search_url):
            listing_url = record.get("listing_url")
            if not listing_url or listing_url in seen_urls:
                continue
            seen_urls.add(listing_url)
            urls.append(listing_url)
            self._record_cache[listing_url] = record

        log.info(f"propertyfinder: extracted {len(urls)} listing URLs from search payload")
        return urls

    async def get_details(self, detail_page: Page, url: str) -> Optional[dict]:
        # Kept for BaseScraper compatibility in case another caller still uses the
        # detail-page flow, but the subclass now reads records directly from search.
        cached = self._record_cache.get(url)
        if cached is not None:
            return dict(cached)

        log.warning(f"propertyfinder: missing cached data for {url}")
        return None
