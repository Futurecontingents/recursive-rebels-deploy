import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3] / "Web_srapers_etl_pipe"
sys.path.insert(0, str(ROOT / "scraper"))

from bayut_scraper import (
    DETAIL_URL_PATT,
    SEARCH_BASE,
    BayutScraper,
    _extract_ldjson_fields,
    _parse_ldjson_block,
    _skip_this,
)

# print("debug:", ROOT)


# helpers to build fake HTML / LD+JSON blobs

def _make_ldjson_html(ld_node: dict) -> str:
    # wrap a ld+json node into a minimal page HTML blob
    blob = json.dumps(ld_node)
    return f'<html><head><script type="application/ld+json">{blob}</script></head><body><h1>Test</h1></body></html>'


def _make_listing_node(overrides: dict | None = None) -> dict:
    # base "good" listing node — covers every field _extract_ldjson_fields touches
    base = {
        "@type": "RealEstateListing",
        "name": "Nice flat in Marina | Bayut.com",
        "dateModified": "2026-03-15",
        "datePosted": "2026-03-01",
        "mainEntity": {
            "price": "750000",
            "priceCurrency": "AED",
            "geo": {"latitude": 25.076, "longitude": 55.133},
            "address": {
                "addressRegion": "Dubai",
                "addressLocality": "Dubai Marina",
            },
            "seller": {
                "name": "  Ahmed Al-Farsi  ",
                "memberOf": {"name": "Gulf Realty LLC"},
            },
            "floorSize": {"value": "985.5", "unitText": "Sqft"},
            "numberOfBedrooms": 2,
            "numberOfBathroomsTotal": 2,
            "amenityFeature": [
                {"name": "Pool"},
                {"name": "Gym"},
            ],
            "accommodationCategory": "Apartment",
        },
    }
    if overrides:
        for k, v in overrides.items():
            if k == "mainEntity":
                base["mainEntity"].update(v)
            else:
                base[k] = v
    return base


# ---- actual tests ----

class TestSkipThis(unittest.TestCase):
    def test_known_ad_domains_get_blocked(self):
        # these should all match because they all dump ECONNRESET in playwright
        self.assertTrue(_skip_this("https://www.doubleclick.net/pixel"))
        self.assertTrue(_skip_this("https://hotjar.com/track.js"))
        self.assertTrue(_skip_this("https://analytics.somecdn.com/metric"))
        self.assertTrue(_skip_this("https://www.facebook.com/fbevents.js"))

    def test_legit_domains_pass_through(self):
        self.assertFalse(_skip_this("https://www.bayut.com/property/details-12345678.html"))
        self.assertFalse(_skip_this("https://cdn.bayut.com/images/listing.jpg"))
        self.assertFalse(_skip_this("https://api.mapbox.com/styles/v1/mapbox"))

    def test_case_insensitivity(self):
        # checking again just in case some mixed-case domains
        self.assertTrue(_skip_this("https://HOTJAR.COM/track.js"))
        self.assertTrue(_skip_this("https://Sentry.IO/api/event"))


class TestDetailUrlPattern(unittest.TestCase):
    def test_matches_valid_detail_urls(self):
        urls = [
            "https://www.bayut.com/property/details-12345678.html",
            "/property/details-9876543.html",
            "https://bayut.com/property/details-100000.html",
        ]
        for u in urls:
            self.assertIsNotNone(DETAIL_URL_PATT.search(u), f"should match: {u}")

    def test_rejects_non_detail_urls(self):
        bad = [
            "https://www.bayut.com/for-sale/property/uae/",
            "https://www.bayut.com/for-sale/apartments/dubai/",
            "https://www.bayut.com/property/",
            # short IDs under 5 digits shouldn't match
            "https://www.bayut.com/property/details-123.html",
        ]
        for u in bad:
            self.assertIsNone(DETAIL_URL_PATT.search(u), f"should NOT match: {u}")

    def test_extracts_listing_id(self):
        m = DETAIL_URL_PATT.search("https://www.bayut.com/property/details-98765432.html")
        self.assertEqual(m.group(1), "98765432")


class TestParseLdJsonBlock(unittest.TestCase):
    def test_extracts_root_level_listing(self):
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        rslt = _parse_ldjson_block(html)
        self.assertIn("mainEntity", rslt)

    def test_extracts_listing_from_graph(self):
        # Bayut sometimes wraps everything in a @graph array
        graph_payload = {
            "@graph": [
                {"@type": "WebSite", "name": "Bayut"},
                _make_listing_node(),
            ]
        }
        html = _make_ldjson_html(graph_payload)
        rslt = _parse_ldjson_block(html)
        self.assertIn("mainEntity", rslt)

    def test_returns_empty_dict_when_no_ldjson_present(self):
        html = "<html><body><h1>Not found</h1></body></html>"
        rslt = _parse_ldjson_block(html)
        self.assertEqual(rslt, {})

    def test_returns_empty_dict_for_completely_empty_html(self):
        rslt = _parse_ldjson_block("")
        self.assertEqual(rslt, {})

    def test_skips_broken_json_blocks(self):
        # one good block after a broken one — parser should recover and find the good one
        bad_block = '<script type="application/ld+json">NOT_VALID_JSON</script>'
        good_node = _make_listing_node()
        good_block = f'<script type="application/ld+json">{json.dumps(good_node)}</script>'
        html = f"<html><head>{bad_block}{good_block}</head></html>"
        rslt = _parse_ldjson_block(html)
        self.assertIn("mainEntity", rslt)

    def test_ignores_non_listing_graph_nodes(self):
        # @graph with only a WebSite node — should return empty
        graph_payload = {
            "@graph": [
                {"@type": "WebSite", "name": "Bayut"},
            ]
        }
        html = _make_ldjson_html(graph_payload)
        rslt = _parse_ldjson_block(html)
        self.assertEqual(rslt, {})


class TestExtractLdJsonFields(unittest.TestCase):
    def test_all_fields_populate_on_complete_node(self):
        node = _make_listing_node()
        flds = _extract_ldjson_fields(node)

        self.assertEqual(flds["price"], 750000)
        self.assertEqual(flds["currency"], "AED")
        self.assertAlmostEqual(flds["lat"], 25.076)
        self.assertAlmostEqual(flds["lng"], 55.133)
        self.assertIn("Dubai Marina", flds["location"])
        self.assertIn("Dubai", flds["location"])
        self.assertEqual(flds["agent"], "Ahmed Al-Farsi")  # strip_val trims the whitespace
        self.assertEqual(flds["company"], "Gulf Realty LLC")
        self.assertAlmostEqual(flds["sz_val"], 985.5)
        self.assertEqual(flds["sz_unit"], "sqft")
        self.assertEqual(flds["beds"], 2)
        self.assertEqual(flds["baths"], 2)
        self.assertEqual(flds["lst_date"], "2026-03-15")  # dateModified wins over datePosted
        self.assertEqual(flds["amenities"], "Pool; Gym")
        self.assertEqual(flds["prop_type"], "Apartment")

    def test_price_as_string_gets_cast_to_int(self):
        # bayut sometimes sends price as a quoted string
        node = _make_listing_node({"mainEntity": {"price": "1250000"}})
        flds = _extract_ldjson_fields(node)
        self.assertEqual(flds["price"], 1250000)
        self.assertIsInstance(flds["price"], int)

    def test_missing_price_returns_none(self):
        node = _make_listing_node()
        del node["mainEntity"]["price"]
        flds = _extract_ldjson_fields(node)
        self.assertIsNone(flds["price"])

    def test_missing_geo_returns_none_coords(self):
        node = _make_listing_node()
        del node["mainEntity"]["geo"]
        flds = _extract_ldjson_fields(node)
        self.assertIsNone(flds["lat"])
        self.assertIsNone(flds["lng"])

    def test_empty_amenities_list_returns_none(self):
        node = _make_listing_node({"mainEntity": {"amenityFeature": []}})
        flds = _extract_ldjson_fields(node)
        self.assertIsNone(flds["amenities"])

    def test_missing_seller_returns_none_agent(self):
        node = _make_listing_node()
        del node["mainEntity"]["seller"]
        flds = _extract_ldjson_fields(node)
        self.assertIsNone(flds["agent"])
        self.assertIsNone(flds["company"])

    def test_datemonified_missing_falls_back_to_dateposted(self):
        node = _make_listing_node()
        del node["dateModified"]
        flds = _extract_ldjson_fields(node)
        self.assertEqual(flds["lst_date"], "2026-03-01")

    def test_both_dates_missing_returns_none(self):
        node = _make_listing_node()
        node.pop("dateModified", None)
        node.pop("datePosted", None)
        flds = _extract_ldjson_fields(node)
        self.assertIsNone(flds["lst_date"])

    def test_entirely_empty_node_returns_none_fields(self):
        # worst case — node has no mainEntity at all
        flds = _extract_ldjson_fields({})
        self.assertIsNone(flds["price"])
        self.assertIsNone(flds["lat"])
        self.assertIsNone(flds["agent"])
        self.assertIsNone(flds["amenities"])

    def test_floor_size_as_non_numeric_string_passed_through(self):
        # site occasionally returns junk like "N/A" — should not crash
        node = _make_listing_node({"mainEntity": {"floorSize": {"value": "N/A", "unitText": "sqft"}}})
        flds = _extract_ldjson_fields(node)
        # strip_val would have been called, result is a stripped string not a float
        # the important thing is it doesn't raise
        self.assertIsNotNone(flds)


class TestBayutScraperBuildUrl(unittest.TestCase):
    def setUp(self):
        # BayutScraper __init__ calls super().__init__() which needs kwargs — keep it minimal
        self.scraper = BayutScraper()

    def test_page_1_returns_base_url(self):
        self.assertEqual(self.scraper.build_url(1), SEARCH_BASE)

    def test_page_0_also_returns_base_url(self):
        # edge case — 0 is <=1 so should still return base
        self.assertEqual(self.scraper.build_url(0), SEARCH_BASE)

    def test_page_2_and_beyond_uses_path_pagination(self):
        self.assertEqual(self.scraper.build_url(2), f"{SEARCH_BASE}page-2/")
        self.assertEqual(self.scraper.build_url(10), f"{SEARCH_BASE}page-10/")


class TestBayutScraperGetDetails(unittest.TestCase):
    """Tests for get_details — all Playwright calls are mocked, no real network."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_mock_page(self, html_content: str, url: str = "https://www.bayut.com/property/details-12345678.html"):
        pg = MagicMock()
        pg.url = url

        # goto returns a fake response with .text() giving our html
        fake_resp = AsyncMock()
        fake_resp.text = AsyncMock(return_value=html_content)
        pg.goto = AsyncMock(return_value=fake_resp)

        # route doesn't need to do anything real
        pg.route = AsyncMock()

        # is_blocked uses page.title() and page.inner_text()
        pg.title = AsyncMock(return_value="Nice flat in Dubai Marina")
        pg.inner_text = AsyncMock(return_value="Normal page content here")

        # query_selector for h1 — returns a mock element
        h1_el = AsyncMock()
        h1_el.inner_text = AsyncMock(return_value="Studio with Sea View in Marina")
        pg.query_selector = AsyncMock(return_value=h1_el)

        return pg

    def test_happy_path_returns_full_record(self):
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        self.assertIsNotNone(rslt)
        self.assertEqual(rslt["listing_id"], "12345678")
        self.assertEqual(rslt["price"], 750000)
        self.assertEqual(rslt["currency"], "AED")
        self.assertEqual(rslt["platform"], "bayut")
        self.assertIn("Dubai Marina", rslt["location"])
        self.assertEqual(rslt["amenities"], "Pool; Gym")

    def test_blocked_page_still_returns_data_when_html_present(self):
        # we keep going even if is_blocked=True as long as we got html
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=True)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        # still returns data — we don't early-exit on is_blocked anymore
        self.assertIsNotNone(rslt)
        self.assertEqual(rslt["listing_id"], "12345678")

    def test_missing_ldjson_triggers_dom_fallback(self):
        # page with no ld+json at all — should fall back to DOM selector path
        html = "<html><body><h1>Some unit</h1></body></html>"
        pg = self._make_mock_page(html)
        # _rd needs query_selector to return something for the fallback fields
        pg.query_selector = AsyncMock(return_value=None)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        # no h1 from query_selector means get_details returns None on DOM fallback
        self.assertIsNone(rslt)

    def test_none_response_from_goto_still_attempts_parse(self):
        # goto can sometimes return None so we fall back to page.content()
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        pg.goto = AsyncMock(return_value=None)
        pg.content = AsyncMock(return_value=html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        self.assertIsNotNone(rslt)
        self.assertEqual(rslt["listing_id"], "12345678")

    def test_output_schema_has_all_required_keys(self):
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        expected_keys = [
            "listing_id", "title", "price", "currency", "location",
            "latitude", "longitude", "property_type", "bedrooms", "bathrooms",
            "size", "size_unit", "developer", "furnishing", "agent",
            "realtor_company", "amenities", "platform", "listing_url", "listing_date",
        ]
        for ky in expected_keys:
            self.assertIn(ky, rslt, f"missing key in schema: {ky}")

    def test_listing_id_extracted_from_url_correctly(self):
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html, url="https://www.bayut.com/property/details-99887766.html")
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-99887766.html"))

        self.assertEqual(rslt["listing_id"], "99887766")

    def test_platform_is_always_bayut(self):
        node = _make_listing_node()
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        self.assertEqual(rslt["platform"], "bayut")

    def test_missing_price_in_ldjson_gives_none_price(self):
        node = _make_listing_node()
        del node["mainEntity"]["price"]
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        self.assertIsNone(rslt["price"])

    def test_missing_location_fields_give_partial_location_string(self):
        node = _make_listing_node({"mainEntity": {"address": {"addressRegion": "Abu Dhabi"}}})
        html = _make_ldjson_html(node)
        pg = self._make_mock_page(html)
        scraper = BayutScraper()

        with patch("bayut_scraper.rnd_sleep", new=AsyncMock()), \
             patch("bayut_scraper.is_blocked", new=AsyncMock(return_value=False)):
            rslt = self._run(scraper.get_details(pg, "https://www.bayut.com/property/details-12345678.html"))

        # addressLocality is gone — location should still have Abu Dhabi and UAE
        self.assertIn("Abu Dhabi", rslt["location"])
        self.assertIn("UAE", rslt["location"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
