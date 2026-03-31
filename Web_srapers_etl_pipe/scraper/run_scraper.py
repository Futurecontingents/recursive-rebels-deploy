# runner — launches one or both scrapers based on CLI args

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper_utils import get_log

log = get_log("Runner")


async def run():
    parser = argparse.ArgumentParser(description="Dubai real estate scraper runner")
    parser.add_argument("--platform", choices=["bayut", "propertyfinder", "all"], default="all")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent.parent / "run_outputs")
    parser.add_argument("--no-headless", action="store_true", default=False)
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-delay", type=float, default=5.0)
    parser.add_argument(
        "--storage-state",
        type=Path,
        help="Optional Playwright storage state file to load before scraping.",
    )
    parser.add_argument(
        "--save-storage-state",
        type=Path,
        help="Optional path to save browser session state after preparing or scraping.",
    )
    parser.add_argument(
        "--prepare-session",
        action="store_true",
        default=False,
        help="Open a visible browser so you can solve a challenge manually and save the session.",
    )

    args = parser.parse_args()

    if args.prepare_session and args.platform == "all":
        parser.error("--prepare-session requires a single platform, not --platform all")

    if args.prepare_session and args.save_storage_state is None:
        args.save_storage_state = args.output_dir / f"{args.platform}_storage_state.json"

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # pass clean, named kwargs so BaseScraper __init__ is easy to read at call site
    scraper_kwargs = {
        "max_pages":  args.max_pages,
        "output_dir": args.output_dir,
        "headless":   False if args.prepare_session else not args.no_headless,
        "min_delay":  args.min_delay,
        "max_delay":  args.max_delay,
        "storage_state": args.storage_state,
        "save_storage_state": args.save_storage_state,
    }

    platforms_to_run = ["bayut", "propertyfinder"] if args.platform == "all" else [args.platform]

    total_collected = 0
    for platform_name in platforms_to_run:
        try:
            # lazy imports so we don't fail at startup if one module has issues
            if platform_name == "bayut":
                from bayut_scraper import BayutScraper
                scraper = BayutScraper(**scraper_kwargs)
            elif platform_name == "propertyfinder":
                from propertyfinder_scraper import PropertyFinderScraper
                scraper = PropertyFinderScraper(**scraper_kwargs)
            else:
                log.warning(f"unknown platform: {platform_name}")
                continue

            log.info(f"starting {platform_name}")
            if args.prepare_session:
                await scraper.prepare_session()
                log.info(
                    f"{platform_name} session prepared and saved to "
                    f"{args.save_storage_state.resolve()}"
                )
            else:
                listings = await scraper.scrape()
                log.info(f"{platform_name} done — {len(listings)} listings")
                total_collected += len(listings)

        except Exception as err:
            log.error(f"{platform_name} failed: {err}")

    log.info(f"all done — {total_collected} total listings saved to {args.output_dir.resolve()}")


if __name__ == "__main__":
    asyncio.run(run())
