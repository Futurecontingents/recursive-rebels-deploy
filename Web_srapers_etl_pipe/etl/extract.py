# extraction phase
import json
from pathlib import Path

RAW_DATA_DIR = Path(__file__).parent.parent / "run_outputs"

def extract(raw_dir: Path = RAW_DATA_DIR) -> list[dict]:
    collected_listings = []

    if not raw_dir.exists():
        # scraper must run before ETL, so this is a hard stop
        raise FileNotFoundError(f"raw data folder missing: {raw_dir}")

    raw_files = sorted(raw_dir.rglob("*.json"))

    if not raw_files:
        print(f"no json files found under {raw_dir}")
        return collected_listings

    for json_file in raw_files:
        try:
            with open(json_file, "r", encoding="utf-8") as fh:
                file_content = json.load(fh)

            # scraper sometimes writes a single dict, sometimes a list — handle both
            if isinstance(file_content, dict):
                page_listings = [file_content]
            elif isinstance(file_content, list):
                page_listings = [entry for entry in file_content if isinstance(entry, dict)]
            else:
                page_listings = []

            collected_listings.extend(page_listings)
            print(f"  {json_file.name}: {len(page_listings)} listings")

        except json.JSONDecodeError as ex:
            print(f"  skipping {json_file.name} — bad JSON: {ex}")
        except Exception as ex:
            print(f"  skipping {json_file.name} — read error: {ex}")

    # print(f"[debug] file count={len(raw_files)}, total={len(collected_listings)}")
    print(f"extracted {len(collected_listings)} total listings from {len(raw_files)} files")
    return collected_listings
