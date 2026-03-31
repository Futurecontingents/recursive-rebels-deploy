# ETL Pipeline Test Plan

These unit tests cover the current ETL flow in `extract.py`, `transform.py`, `load.py`, and the dry-run path in `pipeline.py`.

## What is covered

- `ExtractTests.test_extract_raises_for_missing_input_dir`
  How it tests: creates a temporary path that does not exist and calls `extract()`.
  Expected result: `extract()` raises `FileNotFoundError`.

- `ExtractTests.test_extract_reads_dict_and_list_json_and_skips_bad_entries`
  How it tests: writes one JSON file containing a list, one containing a single dict, and one invalid JSON file.
  Expected result: only valid dict records are returned, in sorted file order, and the invalid file is skipped.

- `ExtractTests.test_extract_returns_empty_list_when_no_json_files_exist`
  How it tests: points `extract()` at an empty temporary directory.
  Expected result: an empty list is returned.

- `TransformTests.test_transform_returns_empty_frame_for_no_records`
  How it tests: calls `transform([])`.
  Expected result: an empty `DataFrame` is returned.

- `TransformTests.test_transform_parses_price_converts_size_and_picks_contact`
  How it tests: sends one raw record with shorthand price (`1.5M`), square-meter size, and a blank `agent_phone` so the broker phone becomes the fallback contact.
  Expected result: price becomes `1500000.0`, size is converted to square feet, bedroom and bathroom fields are numeric, `realtor_contact` uses the broker phone, and no duplicate group is assigned.

- `TransformTests.test_transform_deduplicates_matching_platform_and_listing_ids_only`
  How it tests: sends two identical `platform + listing_id` rows plus two rows with blank listing IDs.
  Expected result: the duplicate keyed row is collapsed, while blank-ID rows are preserved.

- `TransformTests.test_transform_flags_cross_platform_duplicate_groups`
  How it tests: sends a Bayut row and a PropertyFinder row with matching price, beds, baths, and near-identical coordinates.
  Expected result: both rows receive the same non-empty 12-character `duplicate_group_id`.

- `LoadTests.test_load_posts_payloads_and_tracks_ok_dupe_and_failed_counts`
  How it tests: patches `requests.post`, sends one successful listing, one duplicate listing, and one invalid listing missing a required outbound field.
  Expected result: the loader reports one success, one skipped duplicate, one failed record, and only posts the valid payloads to the backend endpoint.

- `PipelineTests.test_exec_pipeline_skips_load_in_dry_run_mode`
  How it tests: mocks `extract`, `transform`, `load`, and `time.perf_counter`, then runs `exec_pipeline(..., dry_run=True)`.
  Expected result: `load()` is not called, counts are still reported, `api_result` stays empty, and elapsed time is returned from the mocked timer values.

## Folder layout

- unit tests: [Docs/etl-pipeline/unit_test](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/unit_test)
- evidence: [Docs/etl-pipeline/evidence](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/evidence)
- passing test evidence: [Docs/etl-pipeline/evidence/unit_test_results.md](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/evidence/unit_test_results.md)

## How to run

```bash
python3 Docs/etl-pipeline/unit_test/test_etl.py -v
```

## Expected suite result

The ETL tests should all pass and report `9` passing tests.

Verified evidence of a passing run is recorded in [Docs/etl-pipeline/evidence/unit_test_results.md](/Users/vaughnprangley/RecursiveRebels/Docs/etl-pipeline/evidence/unit_test_results.md).
