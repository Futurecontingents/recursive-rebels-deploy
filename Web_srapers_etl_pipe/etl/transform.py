# transform phase — cleans raw records and maps them to API-compatible shape

import re
import hashlib
import pandas as pd
import numpy as np


SQM_TO_SQFT = 10.7639

# fields we actually care about — everything else gets dropped before API call
EXPECTED_COLS = [
    "listing_id", "title", "price", "currency", "location",
    "latitude", "longitude", "property_type", "bedrooms",
    "bathrooms", "size", "size_unit", "agent", "realtor_company",
    "platform", "listing_url", "listing_date",
    # PF has these, bayut doesn't — that's fine
    "agent_phone", "broker_phone"
]

strip_non_numeric = re.compile(r"[^\d.]")
sqm_pat = re.compile(r"sq\.?\s*m|m²|sqm", re.IGNORECASE)


def transform(raw_records: list[dict]) -> pd.DataFrame:
    if not raw_records:
        print("no records — returning empty frame")
        return pd.DataFrame()

    df = pd.DataFrame(raw_records)
    print(f"transform input: {len(df)} rows")

    # add missing cols rather than crashing later
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = np.nan

    # drop everything we don't need, keeps frame small
    kept = [c for c in EXPECTED_COLS if c in df.columns]
    df = df[kept].copy()

    # title is our basic sanity check — no title = garbage row
    bfr = len(df)
    df = df[df["title"].notna() & df["title"].astype(str).str.strip().ne("")]
    print(f"dropped {bfr - len(df)} rows missing title")

    # price parsing — handles "1.5M", "800K", comma-separated numbers, plain ints
    def parse_price(raw):
        if pd.isna(raw):
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        txt = str(raw).strip().upper()
        multi = 1.0
        if txt.endswith("M"):
            multi = 1_000_000
            txt = txt[:-1]
        elif txt.endswith("K"):
            multi = 1_000
            txt = txt[:-1]
        cleaned = strip_non_numeric.sub("", txt)
        try:
            return float(cleaned) * multi
        except ValueError:
            return None

    df["price"] = df["price"].apply(parse_price)

    # drop rows where price is missing or zero, backend will reject them anyway
    before_price = len(df)
    df = df[df["price"].notna() & (df["price"] > 0)]
    print(f"dropped {before_price - len(df)} rows with bad price")

    # lat/lon coerce — rows missing these go too since they're required by backend
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    bfr2 = len(df)
    df = df[df["latitude"].notna() & df["longitude"].notna()]
    print(f"dropped {bfr2 - len(df)} rows missing coords")

    # also required by backend — listing_url maps to source_url
    df = df[df["listing_url"].notna() & df["listing_url"].astype(str).str.strip().ne("")]

    # strip commas from size(bayut uses commas)
    def fix_size(row):
        raw_sz = row.get("size")
        unit = str(row.get("size_unit", "sqft"))
        if pd.isna(raw_sz):
            row["size"] = None
            row["size_unit"] = "sqft"
            return row
        numeric = strip_non_numeric.sub("", str(raw_sz))
        try:
            val = float(numeric)
        except ValueError:
            row["size"] = None
            row["size_unit"] = "sqft"
            return row
        # checking again just in case site returns weird data
        if sqm_pat.search(unit):
            val = round(val * SQM_TO_SQFT, 2)
        row["size"] = val
        row["size_unit"] = "sqft"
        return row

    df = df.apply(fix_size, axis=1)

    # bedrooms/bathrooms — PropertyFinder sends them as strings ("2"), bayut as ints
    df["bedrooms"]  = pd.to_numeric(df["bedrooms"],  errors="coerce").astype("Int64")
    df["bathrooms"] = pd.to_numeric(df["bathrooms"], errors="coerce").astype("Int64")

    # contact. PF has agent_phone, bayut doesn't have any phone at all
    # broker_phone is fallback if agent_phone is blank
    def pick_contact(row):
        ap = row.get("agent_phone")
        bp = row.get("broker_phone")
        if not pd.isna(ap) and str(ap).strip():
            return str(ap).strip()
        if not pd.isna(bp) and str(bp).strip():
            return str(bp).strip()
        return None

    df["realtor_contact"] = df.apply(pick_contact, axis=1)

    # exact dedup by platform+listing_id — avoids re-sending same listing from multiple files
    bfr3 = len(df)
    has_id = df["listing_id"].notna() & df["listing_id"].astype(str).str.strip().ne("")
    duped_rows = df[has_id].drop_duplicates(subset=["platform", "listing_id"], keep="first")
    no_id_rows = df[~has_id]
    df = pd.concat([duped_rows, no_id_rows], ignore_index=True)
    print(f"dedup: {bfr3} -> {len(df)}")

    # cross-platform dupe flagging (same price/beds/baths at same coords = same property)
    df["duplicate_group_id"] = ""
    df["_lat3"] = df["latitude"].round(3)
    df["_lon3"] = df["longitude"].round(3)

    match_cols = ["price", "bedrooms", "bathrooms", "_lat3", "_lon3"]
    fk = df[df[match_cols].notna().all(axis=1)].copy()

    # print("debug:", fk.shape)

    if not fk.empty:
        for gkey, gidx in fk.groupby(match_cols, dropna=True).groups.items():
            if len(gidx) < 2:
                continue
            ks = "_".join(str(v) for v in gkey)
            ghash = hashlib.sha1(ks.encode()).hexdigest()[:12]
            df.loc[gidx, "duplicate_group_id"] = ghash

    df.drop(columns=["_lat3", "_lon3"], inplace=True)
    flagged = (df["duplicate_group_id"] != "").sum()
    print(f"cross-platform dupes flagged: {flagged}")

    df = df.reset_index(drop=True)
    print(f"transform output: {len(df)} rows")
    return df


def to_api_payload(row: dict) -> dict:
    # maps one dataframe row to the exact shape ListingRequestDTO expects
    def safe_int(v):
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def safe_float(v):
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def safe_str(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v).strip()
        return s if s and s.lower() != "nan" else None

    payload = {
        "title":           safe_str(row.get("title")),
        "price":           safe_float(row.get("price")),
        "latitude":        safe_float(row.get("latitude")),
        "longitude":       safe_float(row.get("longitude")),
        "source_url":      safe_str(row.get("listing_url")),
        "bedrooms":        safe_int(row.get("bedrooms")),
        "bathrooms":       safe_int(row.get("bathrooms")),
        "area_sqft":       safe_float(row.get("size")),
        "source_site":     safe_str(row.get("platform")),
        "realtor_name":    safe_str(row.get("agent")),
        "realtor_contact": safe_str(row.get("realtor_contact")),
    }
    return payload
