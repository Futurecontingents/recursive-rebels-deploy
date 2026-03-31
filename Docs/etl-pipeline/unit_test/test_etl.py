import json
import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[3] / "Web_srapers_etl_pipe"
ETL_DIR = ROOT / "etl"


def load_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


extract_module = load_module("extract", ETL_DIR / "extract.py")
transform_module = load_module("transform", ETL_DIR / "transform.py")
load_api_module = load_module("load", ETL_DIR / "load.py")
pipeline_module = load_module("etl_pipeline_under_test", ETL_DIR / "pipeline.py")


def make_raw_record(**overrides) -> dict:
    record = {
        "listing_id": "PF-001",
        "title": "Prime Apartment",
        "price": "120000",
        "currency": "AED",
        "location": "Dubai Marina",
        "latitude": "25.1004",
        "longitude": "55.2004",
        "property_type": "Apartment",
        "bedrooms": "2",
        "bathrooms": "2",
        "size": "1308",
        "size_unit": "sqft",
        "agent": "Alice",
        "agent_phone": "+971500000001",
        "broker_phone": "+971400000001",
        "realtor_company": "Acme Realty",
        "platform": "propertyfinder",
        "listing_url": "https://example.com/listing/PF-001",
        "listing_date": "2026-03-17T06:40:22Z",
    }
    record.update(overrides)
    return record


class ExtractTests(unittest.TestCase):
    def test_extract_raises_for_missing_input_dir(self):
        with TemporaryDirectory() as tmp_dir:
            missing_dir = Path(tmp_dir) / "missing"

            with self.assertRaises(FileNotFoundError):
                extract_module.extract(missing_dir)

    def test_extract_reads_dict_and_list_json_and_skips_bad_entries(self):
        with TemporaryDirectory() as tmp_dir:
            raw_dir = Path(tmp_dir)

            (raw_dir / "a_page.json").write_text(
                json.dumps(
                    [
                        {"listing_id": "1"},
                        "ignore me",
                        {"listing_id": "2"},
                    ]
                ),
                encoding="utf-8",
            )
            (raw_dir / "b_page.json").write_text(
                json.dumps({"listing_id": "3"}),
                encoding="utf-8",
            )
            (raw_dir / "c_page.json").write_text("{bad json", encoding="utf-8")

            records = extract_module.extract(raw_dir)

            self.assertEqual([record["listing_id"] for record in records], ["1", "2", "3"])

    def test_extract_returns_empty_list_when_no_json_files_exist(self):
        with TemporaryDirectory() as tmp_dir:
            records = extract_module.extract(Path(tmp_dir))

            self.assertEqual(records, [])


class TransformTests(unittest.TestCase):
    def test_transform_returns_empty_frame_for_no_records(self):
        frame = transform_module.transform([])

        self.assertIsInstance(frame, pd.DataFrame)
        self.assertTrue(frame.empty)

    def test_transform_parses_price_converts_size_and_picks_contact(self):
        frame = transform_module.transform(
            [
                make_raw_record(
                    price="1.5M",
                    size="100",
                    size_unit="sq m",
                    agent_phone="",
                    broker_phone="+971400000009",
                )
            ]
        )

        row = frame.iloc[0]

        self.assertAlmostEqual(row["price"], 1_500_000.0)
        self.assertAlmostEqual(row["size"], 1076.39)
        self.assertEqual(row["size_unit"], "sqft")
        self.assertEqual(int(row["bedrooms"]), 2)
        self.assertEqual(int(row["bathrooms"]), 2)
        self.assertEqual(row["realtor_contact"], "+971400000009")
        self.assertEqual(row["duplicate_group_id"], "")

    def test_transform_deduplicates_matching_platform_and_listing_ids_only(self):
        frame = transform_module.transform(
            [
                make_raw_record(listing_id="PF-001", platform="propertyfinder"),
                make_raw_record(
                    listing_id="PF-001",
                    platform="propertyfinder",
                    title="This later duplicate should be dropped",
                ),
                make_raw_record(
                    listing_id="",
                    platform="propertyfinder",
                    title="No ID listing A",
                    listing_url="https://example.com/listing/no-id-a",
                ),
                make_raw_record(
                    listing_id="",
                    platform="propertyfinder",
                    title="No ID listing B",
                    listing_url="https://example.com/listing/no-id-b",
                ),
            ]
        )

        self.assertEqual(len(frame), 3)
        self.assertEqual((frame["listing_id"] == "PF-001").sum(), 1)
        self.assertEqual((frame["listing_id"].fillna("") == "").sum(), 2)

    def test_transform_flags_cross_platform_duplicate_groups(self):
        frame = transform_module.transform(
            [
                make_raw_record(
                    listing_id="PF-001",
                    platform="propertyfinder",
                    price="95000",
                    latitude="25.1234",
                    longitude="55.5674",
                ),
                make_raw_record(
                    listing_id="BY-001",
                    platform="bayut",
                    price="95000",
                    latitude="25.12349",
                    longitude="55.56749",
                    listing_url="https://example.com/listing/BY-001",
                ),
            ]
        )

        duplicate_ids = set(frame["duplicate_group_id"])

        self.assertEqual(len(duplicate_ids), 1)
        duplicate_id = duplicate_ids.pop()
        self.assertTrue(duplicate_id)
        self.assertEqual(len(duplicate_id), 12)


class LoadTests(unittest.TestCase):
    def test_load_posts_payloads_and_tracks_ok_dupe_and_failed_counts(self):
        listings_df = pd.DataFrame(
            [
                {
                    "title": "Prime Apartment",
                    "price": 120000.0,
                    "latitude": 25.1004,
                    "longitude": 55.2004,
                    "listing_url": "https://example.com/listing/PF-001",
                    "bedrooms": 2,
                    "bathrooms": 2,
                    "size": 1308.0,
                    "platform": "propertyfinder",
                    "agent": "Alice",
                    "realtor_contact": "+971500000001",
                },
                {
                    "title": "Prime Apartment",
                    "price": 125000.0,
                    "latitude": 25.1005,
                    "longitude": 55.2005,
                    "listing_url": "https://example.com/listing/PF-002",
                    "bedrooms": 2,
                    "bathrooms": 2,
                    "size": 1310.0,
                    "platform": "propertyfinder",
                    "agent": "Alice",
                    "realtor_contact": "+971500000001",
                },
                {
                    "title": "Missing URL",
                    "price": 90000.0,
                    "latitude": 25.2,
                    "longitude": 55.3,
                    "listing_url": "",
                    "bedrooms": 1,
                    "bathrooms": 1,
                    "size": 700.0,
                    "platform": "propertyfinder",
                    "agent": "Cara",
                    "realtor_contact": "+971500000003",
                },
            ]
        )

        created = Mock(status_code=201, content=b"")
        duplicate = Mock(status_code=400, content=b'{"error":"duplicate listing"}')
        duplicate.json.return_value = {"error": "duplicate listing"}

        with patch.object(load_api_module.requests, "post", side_effect=[created, duplicate]) as post_mock:
            result = load_api_module.load(listings_df)

        self.assertEqual(result["sent"], 3)
        self.assertEqual(result["ok"], 1)
        self.assertEqual(result["skipped_dupe"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(post_mock.call_args_list[0].kwargs["json"]["source_url"], "https://example.com/listing/PF-001")


class PipelineTests(unittest.TestCase):
    def test_exec_pipeline_skips_load_in_dry_run_mode(self):
        clean_df = pd.DataFrame([make_raw_record()])

        with patch.object(pipeline_module, "extract", return_value=[make_raw_record()]) as extract_mock, patch.object(
            pipeline_module, "transform", return_value=clean_df
        ) as transform_mock, patch.object(pipeline_module, "load") as load_mock, patch.object(
            pipeline_module.time, "perf_counter", side_effect=[10.0, 12.5]
        ):
            result = pipeline_module.exec_pipeline(Path("input"), Path("output"), dry_run=True)

        extract_mock.assert_called_once_with(Path("input"))
        transform_mock.assert_called_once()
        load_mock.assert_not_called()
        self.assertEqual(result["raw_count"], 1)
        self.assertEqual(result["clean_count"], 1)
        self.assertEqual(result["api_result"], {})
        self.assertEqual(result["elapsed_s"], 2.5)


if __name__ == "__main__":
    unittest.main()
