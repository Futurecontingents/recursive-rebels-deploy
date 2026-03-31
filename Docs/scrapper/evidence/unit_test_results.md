# Scrapper Unit Test Results Evidence

This file records a verified passing run of the PropertyFinder parser unit test suite.

## Command used

```bash
python3 Docs/scrapper/unit_test/test_propertyfinder_parser.py -v
```

## Verification date

March 29, 2026

## Result summary

- Total tests run: `4`
- Final status: `OK`

## Output excerpt

```text
test_build_search_url_matches_first_page_and_paginated_urls (__main__.PropertyFinderParserTests) ... ok
test_normalize_listing_maps_propertyfinder_fields (__main__.PropertyFinderParserTests) ... ok
test_parse_next_data_and_extract_search_result (__main__.PropertyFinderParserTests) ... ok
test_records_from_search_result_skips_non_property_rows (__main__.PropertyFinderParserTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
```

## Note

The raw local log is stored at `Docs/scrapper/evidence/unit_test_results.log`, but `.log` files are ignored by the repository. This Markdown file is the tracked evidence that teammates can open from the repo.
