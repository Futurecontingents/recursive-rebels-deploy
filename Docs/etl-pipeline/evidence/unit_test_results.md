# Unit Test Results Evidence

This file records a verified passing run of the ETL unit test suite.

## Command used

```bash
python3 Docs/etl-pipeline/unit_test/test_etl.py -v
```

## Verification date

March 29, 2026

## Result summary

- Total tests run: `9`
- Final status: `OK`

## Output excerpt

```text
test_extract_raises_for_missing_input_dir (__main__.ExtractTests) ... ok
test_extract_reads_dict_and_list_json_and_skips_bad_entries (__main__.ExtractTests) ... ok
test_extract_returns_empty_list_when_no_json_files_exist (__main__.ExtractTests) ... ok
test_load_posts_payloads_and_tracks_ok_dupe_and_failed_counts (__main__.LoadTests) ... ok
test_exec_pipeline_skips_load_in_dry_run_mode (__main__.PipelineTests) ... ok
test_transform_deduplicates_matching_platform_and_listing_ids_only (__main__.TransformTests) ... ok
test_transform_flags_cross_platform_duplicate_groups (__main__.TransformTests) ... ok
test_transform_parses_price_converts_size_and_picks_contact (__main__.TransformTests) ... ok
test_transform_returns_empty_frame_for_no_records (__main__.TransformTests) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.023s

OK
```

## Note

The raw local log is stored at `Docs/etl-pipeline/evidence/unit_test_results.log`, but `.log` files are ignored by the repository. This Markdown file is the tracked evidence that teammates can open from the repo.
