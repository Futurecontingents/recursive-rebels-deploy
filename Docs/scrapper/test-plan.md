# Scrapper propertyfinder Test Plan

These unit tests cover the current PropertyFinder parser helpers in `propertyfinder/parser.py`.

### What is covered

- `PropertyFinderParserTests.test_build_search_url_matches_first_page_and_paginated_urls`
  How it tests: calls `build_search_url()` for page `1` and page `3`.
  Expected result: page `1` returns the base search URL and later pages append the correct `?page=` query parameter.

- `PropertyFinderParserTests.test_parse_next_data_and_extract_search_result`
  How it tests: builds a sample `__NEXT_DATA__` payload, parses it, and extracts the nested search result.
  Expected result: the extracted payload contains the expected page metadata and listing array.

- `PropertyFinderParserTests.test_normalize_listing_maps_propertyfinder_fields`
  How it tests: normalizes a sample PropertyFinder listing with location, agent, broker, and amenity data.
  Expected result: key outbound fields such as `listing_id`, `price`, `currency`, `city`, `community`, `building`, `listing_url`, `agent_phone`, and `amenities` are mapped correctly.

- `PropertyFinderParserTests.test_records_from_search_result_skips_non_property_rows`
  How it tests: passes a search result containing one real property row and one non-property row.
  Expected result: only the property row is turned into an output record, and its page/position metadata is preserved.

### Folder layout

- unit tests: [Docs/scrapper/unit_test](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/unit_test)
- evidence: [Docs/scrapper/evidence](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/evidence)
- passing test evidence: [Docs/scrapper/evidence/unit_test_results.md](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/evidence/unit_test_results.md)

### How to run

```bash
python3 Docs/scrapper/unit_test/test_propertyfinder_parser.py -v
```

### Expected suite result

The scraper tests should all pass and report `4` passing tests.

Verified evidence of a passing run is recorded in [Docs/scrapper/evidence/unit_test_results.md](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/evidence/unit_test_results.md).

# Scrapper Bayut Test Plan

### What Each Test Validates
The following text explains what the tests cover

1. **Ad/Tracking Domain Filter (`TestSkipThis`)**: Validates that external domains(not related to bayut) which slow down loading or cause connection errors (`ECONNRESET`) are accurately aborted while valid assets pass through.
2. **URL Matching (`TestDetailUrlPattern`)**: Verifies that generic hub links are skipped and only actual property detail URLs are caught by the regular expression.
3. **Data Extraction (`TestParseLdJsonBlock` & `TestExtractLdJsonFields`)**: Tests both paths of the payload extraction: when it exists natively at the root, and when it is nested within a `@graph` array. It covers turning string prices into numerical values and handling of missing dates/amenities.
4. **Resilience & Fallbacks (`TestBayutScraperGetDetails`)**: Uses a mocked DOM to prove the scraper successfully extracts fallback values (via standard DOM selectors) if the required JSON-LD script blocks are missing or scrubbed.

### Edge Case Handling
- **Missing Nodes**: Properties without sellers, sizes, or geodata return `None` rather than triggering `KeyError`.
- **Blocked Pages**: If a page is visually "blocked" but the HTML DOM still arrives, the parsing proceeds rather than prematurely exiting.
- **Malformed Inputs**: Test coverage ensures broken JSON structures inside the script tag do not crash the fallback search capabilities.

### Command to run
Activate the virtual inviroemtn then navigate to the unit_test directory in the scrapper directory in docs then run the following command:

```bash
python test_bayut_scraper.py -v
```

### Expected suite result

The scraper tests should all pass and report the passing tests.

Verified evidence of a passing run is recorded in [Docs/scrapper/evidence/bayut_unit_test_results.md]