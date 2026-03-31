import json
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from propertyfinder.constants import SEARCH_BASE_URL, SITE_ROOT


def build_search_url(page_num: int, base_url: str = SEARCH_BASE_URL) -> str:
    if page_num < 1:
        raise ValueError("page_num must be at least 1")

    parsed_url = urlparse(base_url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
        if key != "page"
    ]

    if page_num > 1:
        query_items.append(("page", str(page_num)))

    return urlunparse(parsed_url._replace(query=urlencode(query_items)))


def parse_next_data(raw_payload: str) -> dict[str, Any]:
    if not raw_payload:
        raise ValueError("missing __NEXT_DATA__ payload")
    return json.loads(raw_payload)


def extract_search_result(next_data: dict[str, Any]) -> dict[str, Any]:
    page_props = next_data.get("props", {}).get("pageProps", {})
    search_result = page_props.get("searchResult")
    if not isinstance(search_result, dict):
        raise ValueError("could not find searchResult in __NEXT_DATA__ payload")
    return search_result


def absolute_url(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    return urljoin(SITE_ROOT, path_or_url)


def contact_value(property_data: dict[str, Any], contact_type: str) -> str:
    for option in property_data.get("contact_options") or []:
        if option.get("type") == contact_type:
            return option.get("value") or ""
    return ""


def parse_location_tree(location_tree: list[dict[str, Any]]) -> dict[str, str]:
    location_parts = {
        "city": "",
        "community": "",
        "subcommunity": "",
        "building": "",
    }

    for node in location_tree or []:
        node_type = (node.get("type") or "").upper()
        name = node.get("name") or ""
        if node_type == "CITY" and not location_parts["city"]:
            location_parts["city"] = name
        elif node_type == "COMMUNITY" and not location_parts["community"]:
            location_parts["community"] = name
        elif node_type == "SUBCOMMUNITY" and not location_parts["subcommunity"]:
            location_parts["subcommunity"] = name
        elif node_type in {"TOWER", "BUILDING", "COMPOUND", "VILLA"} and not location_parts["building"]:
            location_parts["building"] = name

    if not location_parts["building"] and location_tree:
        location_parts["building"] = location_tree[-1].get("name") or ""

    return location_parts


def normalize_listing(
    property_data: dict[str, Any],
    page_num: int,
    position: Optional[int] = None,
    aggregated_position: Optional[int] = None,
    search_url: Optional[str] = None,
) -> dict[str, Any]:
    price = property_data.get("price") or {}
    size = property_data.get("size") or {}
    location = property_data.get("location") or {}
    coordinates = location.get("coordinates") or {}
    agent = property_data.get("agent") or {}
    broker = property_data.get("broker") or {}
    images = property_data.get("images") or []
    first_image = images[0] if images else {}
    location_parts = parse_location_tree(property_data.get("location_tree") or [])
    listing_url = absolute_url(
        property_data.get("share_url") or property_data.get("details_path") or ""
    )
    amenities = property_data.get("amenity_names") or property_data.get("amenities") or []

    return {
        "listing_id": property_data.get("listing_id") or property_data.get("id") or "",
        "title": property_data.get("title") or "",
        "price": price.get("value") or "",
        "currency": price.get("currency") or "AED",
        "location": location.get("full_name") or location.get("path_name") or "",
        "latitude": coordinates.get("lat") or "",
        "longitude": coordinates.get("lon") or "",
        "property_type": property_data.get("property_type") or "",
        "bedrooms": property_data.get("bedrooms") or "",
        "bathrooms": property_data.get("bathrooms") or "",
        "size": size.get("value") or "",
        "size_unit": size.get("unit") or "",
        "agent": agent.get("name") or "",
        "realtor_company": broker.get("name") or "",
        "platform": "propertyfinder",
        "listing_url": listing_url,
        "listing_date": property_data.get("listed_date") or property_data.get("last_refreshed_at") or "",
        "page": page_num,
        "position": position or "",
        "aggregated_position": aggregated_position or "",
        "reference": property_data.get("reference") or "",
        "rera": property_data.get("rera") or "",
        "price_period": price.get("period") or "",
        "offering_type": property_data.get("offering_type") or "",
        "size_unit_raw": size.get("unit") or "",
        "city": location_parts["city"],
        "community": location_parts["community"],
        "subcommunity": location_parts["subcommunity"],
        "building": location_parts["building"] or location.get("name") or "",
        "broker_phone": broker.get("phone") or "",
        "broker_email": broker.get("email") or "",
        "agent_email": contact_value(property_data, "email") or agent.get("email") or "",
        "agent_phone": contact_value(property_data, "phone"),
        "agent_languages": ", ".join(agent.get("languages") or []),
        "amenities": "; ".join(str(item) for item in amenities),
        "is_verified": property_data.get("is_verified", False),
        "is_premium": property_data.get("is_premium", False),
        "is_featured": property_data.get("is_featured", False),
        "is_spotlight_listing": property_data.get("is_spotlight_listing", False),
        "is_exclusive": property_data.get("is_exclusive", False),
        "listing_level": property_data.get("listing_level") or "",
        "image_url": first_image.get("medium") or first_image.get("small") or "",
        "description": property_data.get("description") or "",
        "search_url": search_url or "",
    }


def records_from_search_result(
    search_result: dict[str, Any],
    search_url: Optional[str] = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    meta = search_result.get("meta") or {}
    page_num = meta.get("page") or 1

    for listing in search_result.get("listings") or []:
        if listing.get("listing_type") != "property":
            continue

        property_data = listing.get("property")
        if not isinstance(property_data, dict):
            continue

        records.append(
            normalize_listing(
                property_data,
                page_num=page_num,
                position=listing.get("position"),
                aggregated_position=listing.get("aggregated_position"),
                search_url=search_url,
            )
        )

    return records
