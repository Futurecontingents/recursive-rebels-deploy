# load phase — posts transformed listings to backend API
# used to write CSVs, now it sends HTTP requests instead

import time
import requests
import pandas as pd
from pathlib import Path

API_BASE = "http://127.0.0.1:5000"
LISTINGS_ENDPOINT = f"{API_BASE}/api/listings"

# giving up after this many back-to-back connection errors — site might be down
MAX_CONN_ERRORS = 5


def load(listings_df: pd.DataFrame, out_dir: Path = None) -> dict:
    # out_dir kept in signature so pipeline.py doesn't need changes
    if listings_df is None or listings_df.empty:
        print("nothing to load")
        return {"sent": 0, "ok": 0, "skipped_dupe": 0, "failed": 0}

    # lazy import here so the rest of the module still works if transform isn't imported
    from transform import to_api_payload

    total = len(listings_df)
    ok_cnt = 0
    skip_dupe = 0
    fail_cnt = 0
    conn_errs = 0

    print(f"sending {total} records to {LISTINGS_ENDPOINT}")

    # using while + index instead of for-each — bit easier to add retry logic later
    idx = 0
    while idx < total:
        row = listings_df.iloc[idx].to_dict()
        idx += 1

        payload = to_api_payload(row)

        # skip records that are missing required fields — backend would 400 anyway
        if not payload.get("price") or not payload.get("source_url"):
            fail_cnt += 1
            src = payload.get("source_url", "?")
            print(f"  [skip] missing required field — {src}")
            continue

        try:
            resp = requests.post(
                LISTINGS_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            conn_errs = 0  # reset on successful connection

            if resp.status_code == 201:
                ok_cnt += 1

            elif resp.status_code == 400:
                # adding 1 here because earlier this skipped first item
                body = resp.json() if resp.content else {}
                err_msg = body.get("error", "unknown 400")

                if "duplicate" in err_msg.lower():
                    skip_dupe += 1
                    # print("debug:", payload.get("source_url"))
                else:
                    fail_cnt += 1
                    print(f"  [400] {err_msg} — {payload.get('source_url', '?')}")

            else:
                fail_cnt += 1
                print(f"  [err {resp.status_code}] {payload.get('source_url', '?')}")

        except requests.exceptions.ConnectionError:
            conn_errs += 1
            fail_cnt += 1
            print(f"  [conn error] backend not reachable (attempt {conn_errs})")
            if conn_errs >= MAX_CONN_ERRORS:
                print("  too many connection errors — aborting load")
                break
            time.sleep(1)

        except requests.exceptions.Timeout:
            fail_cnt += 1
            print(f"  [timeout] {payload.get('source_url', '?')}")

        except Exception as ex:
            fail_cnt += 1
            print(f"  [unexpected] {ex}")

    rslt = {
        "sent":          total,
        "ok":            ok_cnt,
        "skipped_dupe":  skip_dupe,
        "failed":        fail_cnt,
    }

    print(f"\nload done — ok:{ok_cnt}  dupes:{skip_dupe}  failed:{fail_cnt}")
    return rslt
