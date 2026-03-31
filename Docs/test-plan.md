# Test Plan

## Frontend

### Scope
Frontend unit testing focuses on deterministic UI logic and data transformation rather than full browser rendering or Leaflet map rendering.

### Planned unit tests
1. `extractPrice()` correctly converts numeric values and formatted strings into numbers.
2. `getPropertyTypeFromBedrooms()` correctly maps bedroom counts to property type labels.
3. `normalizeListing()` correctly maps backend API fields into frontend listing objects.
4. `normalizeListing()` correctly applies default values for missing fields.
5. Filtering by maximum price returns only listings within the selected price range.
6. Filtering by minimum transit score returns only listings above the selected threshold.
7. Filtering by maximum distance returns only listings within the selected distance.
8. Filtering by property type returns only listings of the selected type.
9. Filtering by accessibility returns only listings with accessibility enabled.
10. Filtering with `propertyType = all` does not exclude valid listings.
11. High contrast toggle logic correctly switches the state.
12. Text scaling logic correctly applies the selected font scale.

### Notes
Map rendering and popup rendering are treated as manual/integration checks rather than pure unit tests, since they depend on DOM and Leaflet runtime behaviour.

## ETL Pipeline

Purpose: verify the ETL flow from raw JSON extraction through transformation, API-ready loading, and dry-run pipeline execution.

Planned coverage:
- extraction failure when the input directory is missing
- extraction success with mixed JSON shapes and invalid JSON skipping
- extraction behavior for empty input directories
- transform behavior for empty input
- transform normalization for shorthand prices, square-meter sizes, and realtor contact fallback
- transform deduplication for repeated `platform + listing_id` rows
- transform cross-platform duplicate grouping
- load behavior for successful API posts, duplicate responses, and skipped invalid payloads
- pipeline dry-run behavior where loading is skipped but counts still return

Stored here:
- unit tests: [Docs/etl-pipeline/unit_test](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/unit_test)
- evidence: [Docs/etl-pipeline/evidence](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/evidence)
- detailed ETL notes: [Docs/etl-pipeline/test-plan.md](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/test-plan.md)

Run with:
- `python3 Docs/etl-pipeline/unit_test/test_etl.py -v`

Expected result:
- the ETL test module passes end to end

## Scrappers

### PropertyFinder

Purpose: verify the PropertyFinder parser helpers used by the scraper layer.

Planned coverage:
- first-page and paginated search URL generation
- parsing embedded `__NEXT_DATA__` payloads
- extracting `searchResult` from parsed page props
- normalizing PropertyFinder listing fields into the expected output shape
- skipping non-property rows when building search result records

Stored here:
- unit tests: [Docs/scrapper/unit_test](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/unit_test)
- evidence: [Docs/scrapper/evidence](/Users/vaughnprangley/RecursiveRebels/Docs/scrapper/evidence)

Run with:
- `python3 Docs/scrapper/unit_test/test_propertyfinder_parser.py -v`

Expected result:
- the scraper parser test module passes end to end

### Scrapper Bayut Test Plan

Coverage of tests

- aborts going to external domains
- porperly only catches urls of listings through the regular expresion
- test if it can properly parse the LD-Json blocks when its stored at the root or nesteld in a @graph, and makes sure it can parse size and price if they are strings
- tests if it propelry uses DOM fallback values when the LD-Json is missing or scrubbed
- Tests if broken json blocks break the DOM fallback search capabilities

### Command to run
Activate the virtual enviroment then navigate to the unit_test directory in the scrapper directory in docs then run the following command:

```bash
python test_bayut_scraper.py -v
```

### Expected suite result

The scraper tests should all pass and report the passing tests.

Verified evidence of a passing run is recorded in [Docs/scrapper/evidence/bayut_unit_test_results.md]

## Integration Tests

Purpose: Verify an entire run of the app works by 
-> extracting raw HTML mock files (Bayut + PropertyFinder) 
-> through the ETL layer 
-> sending it to the backend `POST /api/listings` API 
-> ensuring that distance, scoring, and data retrieval from the api `GET /api/listings` is correct. 

Stored here:
- integration test: `Docs/integration-tests/test_integration.py`

- logic explanation: `Docs/integration-tests/integration-test.md`
- evidence: `Docs/integration-tests/Evidance/test_results.log`

Run with:
From root directory with the virtual environment activated:
- `python Docs/integration-tests/test_integration.py`

Expected result:
All tests display `[OK]` output as recorded in `test_results.log`
temp database and backend created ran and removed following the existing schema