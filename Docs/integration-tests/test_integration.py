# integration test — validates full pipeline from mock HTML => backend API
# covers bayut + propertyfinder scrapers, transit distance calc, and scoring

import sys
import os
import re
import json
import math
import sqlite3
import requests
import threading
import time

# so we can import scraper parsers + ETL helpers from the project tree
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
back_dir = os.path.join(proj_root, "Backend")
scraper_dir = os.path.join(proj_root, "Web_srapers_etl_pipe", "scraper")
etl_dir     = os.path.join(proj_root, "Web_srapers_etl_pipe", "etl")
mock_data_dir    = os.path.join(os.path.dirname(__file__), "Mock_example_data")

sys.path.insert(0, back_dir)
sys.path.insert(0, scraper_dir)
sys.path.insert(0, etl_dir)


# STEP 1 — Hardcoding the expected values
# pre-calculated offline before running the system (math in explanation.md)

# Bayut listing coords — extracted from Bayut_listingpage_mock.html JSON-LD block
Bayut_lat = 24.862833525277
bayut_lon = 55.141468873901

# PF listing coords — from __NEXT_DATA__ embedded JSON
pf_lat = 25.20560073852539
pf_lon = 55.35015106201172

# transit mocks — deliberately placed at known offsets from the listings
# using 300 meters for metro, 600 meters for bus, 300 meters for pf metro
mock_trns = [
    {
        "name":  "Mock Metro A",
        "type":  "Metro",
        "lat":   Bayut_lat + (300 / 111320.0),
        "lon":   bayut_lon,
    },
    {
        "name":  "Mock Bus A",
        "type":  "Bus",
        "lat":   Bayut_lat - (600 / 111320.0),
        "lon":   bayut_lon,
    },
    {
        "name":  "Mock Metro B",
        "type":  "Metro",
        "lat":   pf_lat + (300 / 111320.0),
        "lon":   pf_lon,
    },
]

# expected values for each listing — hardcoded from offline calculation
# see Evidance/explanation.md for derivation steps
EXPECTED = {
    "bayut": {
        "dist_transit":  299.66,
        "final_score":   8.48,
        "score_band":    "High",
    },
    "pf": {
        "dist_transit":  299.66,
        "final_score":   6.0,
        "score_band":    "Medium",
    },
}

TOLERANCE = 2.0  # allow ±2m on distance, ±0.05 on scores

# print("debug:", MOCK_TRANSIT)


# STEP 2 — PARSE MOCK HTML FILES
# bypass actual scraper network — just feed the saved HTML
def parse_bayut_listing():
    html_path = os.path.join(mock_data_dir, "Bayut_listingpage_mock.html")
    with open(html_path, "r", encoding="utf-8") as fh:
        pg_html = fh.read()

    # reuse bayut scraper's own parser functions — no network, no browser
    import bayut_scraper
    ld_node = bayut_scraper._parse_ldjson_block(pg_html)
    if not ld_node:
        raise RuntimeError("bayut mock: no JSON-LD block found in HTML — check mock file")

    flds = bayut_scraper._extract_ldjson_fields(ld_node)

    # build a record that matches what bayut_scraper.get_details() would return
    # using a fake listing_url
    rec = {
        "listing_id":      "mock-bayut-001",
        "title":           ld_node.get("name", "Mock Bayut Listing"),
        "price":           flds["price"],
        "currency":        flds["currency"],
        "location":        flds["location"],
        "latitude":        flds["lat"],
        "longitude":       flds["lng"],
        "property_type":   flds["prop_type"],
        "bedrooms":        flds["beds"],
        "bathrooms":       flds["baths"],
        "size":            flds["sz_val"],
        "size_unit":       flds["sz_unit"],
        "agent":           flds["agent"],
        "realtor_company": flds["company"],
        "amenities":       flds["amenities"],
        "platform":        "bayut",
        "listing_url":     "https://www.bayut.com/property/details-MOCK001.html",
        "listing_date":    flds["lst_date"],
    }
    return rec


def parse_pf_listing():
    html_path = os.path.join(mock_data_dir, "propertyfinder_mock.html")
    with open(html_path, "r", encoding="utf-8") as fh:
        pg_html = fh.read()

    # property finder scraper embeds all data in __NEXT_DATA__
    from propertyfinder.parser import parse_next_data, extract_search_result, records_from_search_result

    nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', pg_html, re.DOTALL)
    if not nd_match:
        raise RuntimeError("propertyfinder mock: __NEXT_DATA__ block not found — check mock file")

    nd_data = parse_next_data(nd_match.group(1))
    srch_rslt = extract_search_result(nd_data)
    recs = records_from_search_result(srch_rslt, search_url="https://mock.pf.local/")

    if not recs:
        raise RuntimeError("propertyfinder mock: no listing records extracted from __NEXT_DATA__")

    rec = recs[0]
    # override the listing_url so it doesn't clash with bayut duplicate check
    rec["listing_url"] = "https://www.propertyfinder.ae/en/property-MOCK002.html"
    return rec


# STEP 3 — ETL TRANSFORM + PAYLOAD BUILD
# run the normal ETL transform on the raw records (validates that too)
def build_payloads(raw_recs):
    from transform import transform, to_api_payload

    df = transform(raw_recs)
    if df.empty:
        raise RuntimeError("ETL transform returned empty dataframe — likely missing required fields")

    payloads = []
    i = 0
    j = len(df)
    while i < j:
        row = df.iloc[i].to_dict()
        i += 1
        pl = to_api_payload(row)
        if not pl.get("price") or not pl.get("source_url"):
            print(f"  skip building the payloads missing required field in row {i}")
            continue
        payloads.append(pl)

    return payloads



# STEP 4 — BACKEND SETUP: isolated test DB + inject transit mocks
# we use a separate db so the real property.db isnt touched
TEST_DB = os.path.join(back_dir, "test_integration.db")
Schema_file = os.path.join(back_dir, "database.sql")

def setup_test_db():
    # wipe any leftover test db from last run
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(Schema_file, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()

    for tp in mock_trns:
        conn.execute(
            "INSERT INTO TRANSIT_POINT (StationName, Type, Latitude, Longitude) VALUES (?,?,?,?)",
            (tp["name"], tp["type"], tp["lat"], tp["lon"])
        )
    conn.commit()
    conn.close()
    print(f"test DB ready: {TEST_DB}, transit points: {len(mock_trns)}")


def teardown_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("test DB cleaned up")



# STEP 5 — start test flask server using the test database
def _build_test_app():
    # need to clear cached modules so we can re-import with the patched db path
    for mod in list(sys.modules.keys()):
        if any(k in mod for k in ["ListingRoutes", "ListingRepository", "ListingService", "ListingDTO"]):
            del sys.modules[mod]

    from flask import Flask
    from routes import ListingRoutes
    
    # update property.db to our test db
    ListingRoutes.repository.db_file = TEST_DB

    app = Flask(__name__, template_folder=proj_root, static_folder=proj_root)
    app.register_blueprint(ListingRoutes.listing_bp)
    return app


def start_test_server():
    global flask_app, server_thread

    flask_app = _build_test_app()
    flask_app.config["TESTING"] = True

    def run():
        # quiet=True keeps werkzeug logs suppressed during tests
        flask_app.run(host="127.0.0.1", port=5099, use_reloader=False)

    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()
    # give it a moment to bind properly
    time.sleep(1.5)
    print("test server up on :5099")


TEST_BASE = "http://127.0.0.1:5099"


# STEP 6 — helpers for deciding pass or fail
def assert_close(label, actual, expected, tol):
    diff = abs((actual or 0.0) - expected)
    if (diff<= tol):
        status = "PASS"
    else:
        status = "FAIL"
    print(f"  [{status}] {label}: expected={expected}, actual={actual}, diff={round(diff,4)}, tol={tol}")
    if status == "FAIL":
        raise AssertionError(f"FAIL — {label}: expected {expected} got {actual} (diff={round(diff,4)}, tol={tol})")

def assert_eq(label, actual, expected):
    if(actual == expected):
        status = "PASS"
    else:
        status = "FAIL"
    print(f"  [{status}] {label}: expected={repr(expected)}, actual={repr(actual)}")
    if status == "FAIL":
        raise AssertionError(f"FAIL — {label}: expected {repr(expected)} got {repr(actual)}")



# STEP 7 — POST LISTINGS to backend api
def post_and_fetch(payload):
    resp = requests.post(
        f"{TEST_BASE}/api/listings",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if resp.status_code != 201:
        raise RuntimeError(f"POST /api/listings failed: {resp.status_code} — {resp.text}")

    listing_id = resp.json()["listingId"]

    # fetch it back to get the computed score fields
    get_resp = requests.get(f"{TEST_BASE}/api/listings/{listing_id}", timeout=10)
    if get_resp.status_code != 200:
        raise RuntimeError(f"GET /api/listings/{listing_id} failed: {get_resp.status_code}")

    return get_resp.json()


# STEP 8 — RUN TESTS
def run_tests():
    results = []

    print("INTEGRATION TEST — RUNNING")

    # test 1: bayut listing
    print("\n[TEST 1] Bayut listing — transit distance + score")
    try:
        bayut_raw = parse_bayut_listing()
        payloads = build_payloads([bayut_raw])
        if not payloads:
            raise RuntimeError("no valid payload built from bayut mock")

        listing_data = post_and_fetch(payloads[0])
        dist = listing_data.get("distanceToNearestTransit")
        score = listing_data.get("finalScore")
        band = listing_data.get("scoreBand")

        print(f"  raw response: dist={dist}, score={score}, band={band}")

        assert dist is not None and dist != 0, f"FAIL — distance is {dist} (bug: should not be None or 0)"
        assert_close("bayut dist_transit", dist,  EXPECTED["bayut"]["dist_transit"], TOLERANCE)
        assert_close("bayut final_score",  score, EXPECTED["bayut"]["final_score"],  0.05)
        assert_eq("bayut score_band", band, EXPECTED["bayut"]["score_band"])

        results.append(("TEST 1 — Bayut transit validation", "PASS"))

    except Exception as ex:
        results.append(("TEST 1 — Bayut transit validation", f"FAIL: {ex}"))

    # test 2: propertyfinder listing (edge case: no bus near it)
    print("\n[TEST 2] PropertyFinder listing — no nearby bus, score degraded")
    try:
        pf_raw = parse_pf_listing()
        payloads = build_payloads([pf_raw])
        if not payloads:
            raise RuntimeError("no valid payload built from pf mock")

        listing_data = post_and_fetch(payloads[0])
        dist = listing_data.get("distanceToNearestTransit")
        score = listing_data.get("finalScore")
        band = listing_data.get("scoreBand")

        print(f"  raw response: dist={dist}, score={score}, band={band}")

        assert dist is not None and dist != 0, f"FAIL — distance is {dist} (bug: should not be None or 0)"
        assert_close("pf dist_transit", dist,  EXPECTED["pf"]["dist_transit"], TOLERANCE)
        assert_close("pf final_score",  score, EXPECTED["pf"]["final_score"],  0.05)
        assert_eq("pf score_band", band, EXPECTED["pf"]["score_band"])

        results.append(("TEST 2 — PF transit validation (no bus)", "PASS"))

    except Exception as ex:
        results.append(("TEST 2 — PF transit validation (no bus)", f"FAIL: {ex}"))

    # test 3: detecting dublicates
    print("\n[TEST 3] Duplicate listing rejected")
    try:
        bayut_raw = parse_bayut_listing()
        payload = build_payloads([bayut_raw])[0]

        dup_resp = requests.post(
            f"{TEST_BASE}/api/listings",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        assert dup_resp.status_code == 400, f"expected 400 for dup, got {dup_resp.status_code}"
        err_body = dup_resp.json()
        assert "duplicate" in err_body.get("error", "").lower(), f"unexpected error msg: {err_body}"

        results.append(("TEST 3 — Duplicate rejection", "PASS"))
        print(f"  [PASS] duplicate correctly rejected with 400")

    except Exception as ex:
        results.append(("TEST 3 — Duplicate rejection", f"FAIL: {ex}"))

    # test 4: GET /api/listings includes both listings from scrappers
    print("\n[TEST 4] GET /api/listings makes sure backend api returns both inserted listings")
    try:
        all_resp = requests.get(f"{TEST_BASE}/api/listings", timeout=10)
        all_resp.raise_for_status()
        all_data = all_resp.json()

        # at least 2 items(the two we inserted)
        assert len(all_data) >= 2, f"expected >=2 listings, got {len(all_data)}"
        bad = [x for x in all_data if x.get("distanceToNearestTransit") in (None, 0)]
        assert not bad, f"some listings still have null/0 transit distance: {bad}"

        results.append(("TEST 4 — GET all listings data integrity", "PASS"))
        print(f"  [PASS] {len(all_data)} listings returned with correct none zero transit distance")

    except Exception as ex:
        results.append(("TEST 4 — GET all listings data integrity", f"FAIL: {ex}"))

    # summary
    print("RESULTS SUMMARY")
    failed = 0
    for name, status in results:
        if(status == "PASS"):
            icon = "[OK]"
        else:
            icon = "[FAIL]"
        print(f"  {icon} {name}: {status}")
        if status != "PASS":
            failed += 1

    print(f"\n{'ALL TESTS PASSED' if failed == 0 else f'{failed} TEST(S) FAILED'}")
    return results, failed

# ENTRYPOINT

if __name__ == "__main__":
    try:
        setup_test_db()
        start_test_server()
        results, total_failed = run_tests()
    finally:
        teardown_test_db()

    sys.exit(1 if total_failed > 0 else 0)
