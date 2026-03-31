# Bayut Scrapper Unit Test Results Evidence

This file records a verified passing run of the Bayut scraper unit test suite.

## Command used

```bash
.\.venv\Scripts\python.exe Docs/scrapper/unit_test/test_bayut_scraper.py -v
```

## Verification date

March 30, 2026

## Result summary

- Total tests run: `34`
- Final status: `OK`

## Output excerpt

```text
test_page_1_returns_base_url (__main__.TestBayutScraperBuildUrl) ... ok
test_properly_falls_back_to_dom_selectors (__main__.TestBayutScraperGetDetails) ... ok
test_matches_valid_detail_urls (__main__.TestDetailUrlPattern) ... ok
test_all_fields_populate_on_complete_node (__main__.TestExtractLdJsonFields) ... ok
test_extracts_listing_from_graph (__main__.TestParseLdJsonBlock) ... ok
test_legit_domains_pass_through (__main__.TestSkipThis) ... ok
test_blocked_page_still_returns_data_when_html_present (__main__.TestBayutScraperGetDetails) ... ok

----------------------------------------------------------------------
Ran 34 tests in 0.054s

OK
```

## Note

The raw local log is stored at `Docs/scrapper/evidence/bayut_unit_test_results.log`, but `.log` files are ignored by the repository. This Markdown file is the tracked evidence that teammates can open from the repo.
