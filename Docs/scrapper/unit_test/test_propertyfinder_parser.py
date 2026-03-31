import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "Web_srapers_etl_pipe"
sys.path.insert(0, str(ROOT / "scraper"))

from propertyfinder.constants import SEARCH_BASE_URL
from propertyfinder.parser import (
    build_search_url,
    extract_search_result,
    normalize_listing,
    parse_next_data,
    records_from_search_result,
)


def make_property(listing_id: str = "65151468") -> dict:
    return {
        "id": listing_id,
        "property_type": "Apartment",
        "price": {
            "value": 120000,
            "currency": "AED",
            "period": "yearly",
        },
        "title": "Prime Location | Multiple Vacant | Balcony",
        "location": {
            "full_name": "Majestic Tower, Al Abraj street, Business Bay, Dubai",
            "name": "Majestic Tower",
            "coordinates": {
                "lat": 25.1844,
                "lon": 55.2811,
            },
        },
        "agent": {
            "name": "Muhammad Siddik",
            "email": "muhammad@example.com",
            "languages": ["English", "Urdu"],
        },
        "broker": {
            "name": "Distinguished Real Estate",
            "email": "office@example.com",
            "phone": "+97143438302",
        },
        "bedrooms": "2",
        "bathrooms": "2",
        "size": {
            "value": 1308,
            "unit": "sqft",
        },
        "share_url": "/en/plp/rent/apartment-for-rent-dubai-business-bay-al-abraj-street-majestic-tower-65151468.html",
        "reference": "REF-65151468",
        "listed_date": "2026-03-17T06:40:22Z",
        "last_refreshed_at": "2026-03-18T06:40:22Z",
        "contact_options": [
            {"type": "email", "value": "muhammad@example.com"},
            {"type": "phone", "value": "+971506625719"},
        ],
        "amenities": ["BA", "CP"],
        "furnished": "NO",
        "is_verified": False,
        "is_featured": False,
        "is_premium": True,
        "is_spotlight_listing": True,
        "is_exclusive": False,
        "listing_level": "premium",
        "location_tree": [
            {"type": "CITY", "name": "Dubai"},
            {"type": "COMMUNITY", "name": "Business Bay"},
            {"type": "SUBCOMMUNITY", "name": "Al Abraj street"},
            {"type": "TOWER", "name": "Majestic Tower"},
        ],
        "description": "Direct from owner",
    }


def make_next_data() -> dict:
    return {
        "props": {
            "pageProps": {
                "searchResult": {
                    "meta": {
                        "page": 2,
                        "page_count": 12,
                        "total_count": 300,
                    },
                    "listings": [
                        {
                            "listing_type": "property",
                            "position": 1,
                            "aggregated_position": 26,
                            "property": make_property(),
                        },
                        {
                            "listing_type": "project",
                            "position": 2,
                            "aggregated_position": 27,
                            "property": None,
                        },
                    ],
                }
            }
        }
    }


class PropertyFinderParserTests(unittest.TestCase):
    def test_build_search_url_matches_first_page_and_paginated_urls(self):
        self.assertEqual(build_search_url(1), SEARCH_BASE_URL)
        self.assertEqual(
            build_search_url(3),
            f"{SEARCH_BASE_URL}?page=3",
        )

    def test_parse_next_data_and_extract_search_result(self):
        raw_payload = json.dumps(make_next_data())
        search_result = extract_search_result(parse_next_data(raw_payload))

        self.assertEqual(search_result["meta"]["page"], 2)
        self.assertEqual(len(search_result["listings"]), 2)

    def test_normalize_listing_maps_propertyfinder_fields(self):
        record = normalize_listing(
            make_property(),
            page_num=2,
            position=1,
            aggregated_position=26,
            search_url=build_search_url(2),
        )

        self.assertEqual(record["listing_id"], "65151468")
        self.assertEqual(record["price"], 120000)
        self.assertEqual(record["currency"], "AED")
        self.assertEqual(record["city"], "Dubai")
        self.assertEqual(record["community"], "Business Bay")
        self.assertEqual(record["building"], "Majestic Tower")
        self.assertEqual(record["listing_url"], "https://www.propertyfinder.ae/en/plp/rent/apartment-for-rent-dubai-business-bay-al-abraj-street-majestic-tower-65151468.html")
        self.assertEqual(record["agent_phone"], "+971506625719")
        self.assertEqual(record["amenities"], "BA; CP")

    def test_records_from_search_result_skips_non_property_rows(self):
        records = records_from_search_result(
            extract_search_result(make_next_data()),
            search_url=build_search_url(2),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["page"], 2)
        self.assertEqual(records[0]["position"], 1)


if __name__ == "__main__":
    unittest.main()
