# main etl entry point — extract → transform → load

import argparse
import sys
import time
from pathlib import Path

# needed because etl/ isn't a proper package yet
sys.path.insert(0, str(Path(__file__).parent))

from extract import extract
from transform import transform
from load import load


def exec_pipeline(input_dir: Path, output_dir: Path, dry_run: bool = False) -> dict:
    print("Starting the Dubai real estate ETL pipeline")

    start_time = time.perf_counter()

    print("\n[Phase 1] Extracting the data from 'run_outputs'")
    raw_records = extract(input_dir)

    print("\n[Phase 2] Transforming the data to fit the api")
    clean_df = transform(raw_records)

    # dry_run compared explicitly — avoids treating None as falsy by accident
    api_rslt = {}
    if dry_run == False:
        print("\n[Phase 3] Loading data into the backend api")
        api_rslt = load(clean_df, output_dir)
    else:
        print("\n[Phase 3] Load skipped we are dry running)")

    elapse = time.perf_counter() - start_time

    print("\n" + "-" * 50)
    print(f"  Extracted : {len(raw_records)} records")
    print(f"  Cleaned   : {len(clean_df)} rows")
    print(f"  Time      : {elapse:.1f}s")
    if api_rslt:
        print(f"  -> Sent    : {api_rslt.get('sent', 0)}")
        print(f"  -> OK      : {api_rslt.get('ok', 0)}")
        print(f"  -> Dupes   : {api_rslt.get('skipped_dupe', 0)}")
        print(f"  -> Failed  : {api_rslt.get('failed', 0)}")
    print("-" * 50)

    # print(f"[debug] dry_run={dry_run}, api_rslt={api_rslt}")

    pipeline_result = {
        "raw_count":   len(raw_records),
        "clean_count": len(clean_df),
        "api_result":  api_rslt,
        "elapsed_s":   round(elapse, 2),
    }
    return pipeline_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="etl pipeline script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent.parent / "run_outputs",
        help="dir with raw scraped jsons",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "output",
        help="dir where csvs go",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="skip saving to files",
    )

    args = parser.parse_args()
    exec_pipeline(args.input, args.output, args.dry_run)
