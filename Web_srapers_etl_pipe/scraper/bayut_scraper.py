# bayut scraper — started clean, got messy when SSR pages broke the API intercept approach
# rebuilt around JSON-LD + aria-label selectors after the class-name hashes kept rotating

import json
import re

from playwright.async_api import Page, Route

from base_scraper import BaseScraper
from scraper_utils import get_log, strip_val, is_blocked, rnd_sleep

log = get_log("Bayut")

SEARCH_BASE = "https://www.bayut.com/for-sale/property/uae/"

# this pattern only matches actual detail pages — not category hubs or search URLs
DETAIL_URL_PATT = re.compile(r"/property/details-(\d{5,12})\.html")

# ad/tracking domains — ECONNRESET when playwright tries to fetch through them
_SKIP_DOMAINS = (
    "linkedin.com", "facebook.com", "doubleclick.net", "google-analytics.com",
    "googletagmanager.com", "px.ads.", "analytics.", "hotjar.com",
    "sentry.io", "datadog", "newrelic", "segment.io", "mixpanel",
    "criteo", "bing.com/bat", "clarity.ms", "tiktok.com",
)

# print("debug:", SEARCH_BASE)


def _skip_this(url: str) -> bool:
    low = url.lower()
    return any(d in low for d in _SKIP_DOMAINS)


def _parse_ldjson_block(html_txt: str) -> dict:
    # Bayut embeds structured data in a JSON-LD script tag — far more stable than class selectors
    # the block we want has "mainEntity" inside a @graph or directly at root
    all_blks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html_txt, re.DOTALL | re.IGNORECASE
    )

    idx = 0
    while idx < len(all_blks):
        raw = all_blks[idx]
        idx += 1
        try:
            parsed = json.loads(raw.strip())
        except Exception:
            continue

        if not isinstance(parsed, dict):
            continue

        grph = parsed.get("@graph")
        if grph:
            for node in grph:
                if node.get("@type") == "RealEstateListing" and "mainEntity" in node:
                    return node

        # sometimes the top-level object itself is the listing
        if "mainEntity" in parsed:
            return parsed

    return {}


def _extract_ldjson_fields(ld_node: dict):
    # pull everything we need out of the node in one go rather than multiple helpers
    # keeping it in one function because each field is a one-liner and splitting felt overkill
    ent = ld_node.get("mainEntity") or {}

    # price
    raw_p = ent.get("price")
    currency = ent.get("priceCurrency", "AED")
    if raw_p is not None:
        try:
            price_val = int(raw_p)
        except (ValueError, TypeError):
            price_val = strip_val(str(raw_p))
    else:
        price_val = None

    # geo
    geo    = ent.get("geo") or {}
    lat    = geo.get("latitude")
    lng    = geo.get("longitude")

    # address
    addr     = ent.get("address") or {}
    region   = addr.get("addressRegion") or ""
    locality = addr.get("addressLocality") or ""
    loc_parts = [p for p in [locality, region, "UAE"] if p]
    loc_str  = " > ".join(loc_parts) if loc_parts else None

    # agent + company
    seller   = ent.get("seller") or {}
    agnt     = strip_val(seller.get("name"))
    org      = seller.get("memberOf") or {}
    company  = strip_val(org.get("name"))

    # size
    flr    = ent.get("floorSize") or {}
    sz_raw = flr.get("value")
    sz_unit = (flr.get("unitText") or "sqft").lower()
    if sz_raw is not None:
        try:
            sz_val = float(sz_raw)
        except (ValueError, TypeError):
            sz_val = strip_val(str(sz_raw))
    else:
        sz_val = None

    beds   = ent.get("numberOfBedrooms")
    baths  = ent.get("numberOfBathroomsTotal")

    # dateModified is usually more recent than datePosted
    lst_date = strip_val(ld_node.get("dateModified") or ld_node.get("datePosted"))

    # amenities: list of {name, value} objects
    feats = ent.get("amenityFeature") or []
    amen_names = [f.get("name") for f in feats if f.get("name")]
    amenities = "; ".join(amen_names) if amen_names else None

    prop_type = strip_val(ent.get("accommodationCategory"))

    return {
        "price":      price_val,
        "currency":   currency,
        "lat":        lat,
        "lng":        lng,
        "location":   loc_str,
        "agent":      agnt,
        "company":    company,
        "sz_val":     sz_val,
        "sz_unit":    sz_unit,
        "beds":       beds,
        "baths":      baths,
        "lst_date":   lst_date,
        "amenities":  amenities,
        "prop_type":  prop_type,
    }


class BayutScraper(BaseScraper):
    platform = "bayut"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build_url(self, pg_num: int) -> str:
        # path-based pagination — ?page=N does nothing on bayut
        if pg_num <= 1:
            return SEARCH_BASE
        return f"{SEARCH_BASE}page-{pg_num}/"

    async def _check_landed_correctly(self, pg: Page) -> bool:
        cur = pg.url.lower()
        log.info(f"landed on: {pg.url}")
        if "bayut.com/for-sale" not in cur and "bayut.com/for-rent" not in cur:
            log.warning(f"redirected away from search — got: {pg.url}")
            return False
        if "/property/" not in cur:
            log.warning(f"missing /property/ segment — looks like a category hub: {pg.url}")
            return False
        ttl = (await pg.title()).lower()
        if ttl.strip() in ("bayut", "bayut - uae's no.1 property portal", ""):
            log.warning(f"homepage title — probably got redirected. title='{ttl}'")
            return False
        return True

    async def get_list_urls(self, srch_pg: Page) -> list[str]:
        log.info(f"get_list_urls: scanning {srch_pg.url}")

        found_nodes = False
        wattempt = 0
        while wattempt < 2 and not found_nodes:
            wattempt += 1
            try:
                await srch_pg.wait_for_selector('li[role="article"]', timeout=25_000)
                found_nodes = True
            except Exception:
                log.warning(
                    f"bayut: attempt {wattempt} — timed out on li[role='article'] at {srch_pg.url}"
                )
                if wattempt < 2:
                    log.info("retrying selector wait once more...")
                    await rnd_sleep(2.0, 4.0)

        if not found_nodes:
            log.warning("bayut: listing nodes never appeared — returning empty")
            return []

        # anchors sometimes render just after the li container does
        await rnd_sleep(0.8, 1.6)

        raw_anchors = await srch_pg.query_selector_all(
            'li[role="article"] a[href*="/property/details-"]'
        )
        log.info(f"bayut: found {len(raw_anchors)} raw anchor nodes in listing cards")

        urls = []
        seen = set()
        idx = 0
        while idx < len(raw_anchors):
            href = await raw_anchors[idx].get_attribute("href")
            idx += 1
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.bayut.com" + href
            if not DETAIL_URL_PATT.search(href):
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(href)

        log.info(f"bayut: {len(urls)} valid detail URLs after dedup/filter")
        return urls

    async def get_details(self, dtl_pg: Page, url: str) -> dict:
        # routing handler — just abort ad/tracker requests so they don't slow down the load
        # we don't intercept API responses anymore since detail pages are SSR anyway
        async def noop_trackr(route: Route):
            req_url = route.request.url
            if _skip_this(req_url):
                try:
                    await route.abort()
                except Exception:
                    pass
                return
            try:
                await route.continue_()
            except Exception:
                pass

        await dtl_pg.route("**/*", noop_trackr)

        # custom nav code without the annoying delay pulling html directly
        resp = await dtl_pg.goto(url, wait_until="domcontentloaded", timeout=45_000)
        
        # grabbing early just in case captcha goes crazy
        pg_html = ""
        if resp:
            pg_html = await resp.text()
        else:
            pg_html = await dtl_pg.content()
            
        # simulating the sleep from before so we don't get banned 
        await rnd_sleep(1.0, 2.5)

        # we keep checking to log it but we still parse our html
        isblk = await is_blocked(dtl_pg)
        if isblk:
            log.warning(f"bayut detail blocked (got html though): {url}")
            
        # id extraction 
        id_match = DETAIL_URL_PATT.search(url)
        listing_id = id_match.group(1) if id_match else None

        ld_node  = _parse_ldjson_block(pg_html)

        if ld_node:
            flds = _extract_ldjson_fields(ld_node)

            # h1 text is cleaner than ld_node["name"] because it doesn't have " | Bayut.com"
            pg_title = None
            try:
                h1 = await dtl_pg.query_selector("h1")
                if h1:
                    pg_title = strip_val(await h1.inner_text())
            except Exception:
                pass
            if not pg_title:
                pg_title = strip_val(ld_node.get("name", "").replace(" | Bayut.com", ""))

            prop_type = flds["prop_type"]
            if not prop_type:
                prop_type = await self._rd(dtl_pg, 'span[aria-label="Type"]')

            sz_val  = flds["sz_val"]
            sz_unit = flds["sz_unit"]
            if sz_val is None:
                # DOM fallback for size — old selector accidentally grabbed "Area Guides" footer text
                raw_sz = await self._rd(dtl_pg, 'span[aria-label="Built-up Area"]')
                if raw_sz:
                    cleaned = re.sub(r"[^\d.,]", "", raw_sz.replace(",", ""))
                    try:
                        sz_val = float(cleaned) if cleaned else None
                    except ValueError:
                        sz_val = raw_sz
                    sz_unit = "sqft"

            devlpr  = await self._rd(dtl_pg, 'span[aria-label="Developer"]')
            furnish = await self._rd(dtl_pg, 'span[aria-label="Furnishing"]')

            rslt_data = {
                "listing_id":      listing_id or str(ld_node.get("id", "")),
                "title":           pg_title,
                "price":           flds["price"],
                "currency":        flds["currency"],
                "location":        flds["location"],
                "latitude":        flds["lat"],
                "longitude":       flds["lng"],
                "property_type":   prop_type,
                "bedrooms":        flds["beds"],
                "bathrooms":       flds["baths"],
                "size":            sz_val,
                "size_unit":       sz_unit,
                "developer":       devlpr,
                "furnishing":      furnish,
                "agent":           flds["agent"],
                "realtor_company": flds["company"],
                "amenities":       flds["amenities"],
                "platform":        self.platform,
                "listing_url":     url,
                "listing_date":    flds["lst_date"],
            }
            
            # fully pop check
            req_keys = ["title", "price", "location", "property_type", "listing_id"]
            is_full = True
            for k in req_keys:
                if rslt_data.get(k) is None:
                    is_full = False
                    break
                    
            if is_full:
                print(f"managed sucssesfully to scrape {url}")
                
            return rslt_data

        # only hit this if the JSON-LD block was totally absent — uncommon but does happen
        log.warning(f"bayut: no JSON-LD on {url}, falling back to DOM selectors")

        pg_title = await self._rd(dtl_pg, "h1")
        if not pg_title:
            log.warning(f"bayut: no h1 on {url} — skipping")
            return None

        raw_price = await self._rd(dtl_pg, 'span[aria-label="Price"]')
        if raw_price:
            price_clean = re.sub(r"[^\d.]", "", raw_price)
            try:
                raw_price = int(price_clean)
            except ValueError:
                pass

        raw_curr  = await self._rd(dtl_pg, 'span[aria-label="Currency"]')
        raw_beds  = await self._rd(dtl_pg, 'span[aria-label="Beds"]')
        raw_baths = await self._rd(dtl_pg, 'span[aria-label="Baths"]')

        # targeting inside the basic-info block specifically — the generic aria-label="Area"
        # selector also matches footer nav links which is not what we want
        raw_area = None
        area_el  = await dtl_pg.query_selector('[aria-label="Property basic info"] span[aria-label="Area"]')
        if area_el:
            raw_area = strip_val(await area_el.inner_text())

        raw_loc = await self._rd(dtl_pg, '[aria-label="Property header"]')

        rslt_data = {
            "listing_id":      listing_id,
            "title":           pg_title,
            "price":           raw_price,
            "currency":        raw_curr or "AED",
            "location":        raw_loc,
            "latitude":        None,
            "longitude":       None,
            "property_type":   await self._rd(dtl_pg, 'span[aria-label="Type"]'),
            "bedrooms":        raw_beds,
            "bathrooms":       raw_baths,
            "size":            raw_area,
            "size_unit":       "sqft",
            "developer":       await self._rd(dtl_pg, 'span[aria-label="Developer"]'),
            "furnishing":      await self._rd(dtl_pg, 'span[aria-label="Furnishing"]'),
            "agent":           None,
            "realtor_company": None,
            "amenities":       None,
            "platform":        self.platform,
            "listing_url":     url,
            "listing_date":    await self._rd(dtl_pg, 'span[aria-label="Reactivated date"]'),
        }

        req_keys = ["title", "price", "location", "property_type", "listing_id"]
        is_full = True
        for k in req_keys:
            if rslt_data.get(k) is None:
                is_full = False
                break
                
        if is_full:
            print(f"managed sucssesfully to scrape {url}")
            
        return rslt_data

    async def _rd(self, pg: Page, sel: str) -> str | None:
        # named _rd instead of _dom_attr — shorter, been using it so long the name stuck
        try:
            el = await pg.query_selector(sel)
            if el is None:
                return None
            return strip_val(await el.inner_text())
        except Exception:
            return None
