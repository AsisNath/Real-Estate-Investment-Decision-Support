"""Rebuild data/redfin_markets.json from Redfin's free public housing dataset.

The bundled market_data.json covers four ZIPs by hand. Every other address falls
back to state or national sample figures and the report says so. Redfin publishes
ZIP-level sale data for the whole country as a free download, so the fallback can
be the exception rather than the rule.

Run it when the data feels stale (Redfin refreshes weekly; quarterly is plenty):

    python scripts/refresh_redfin_markets.py

Requires internet. The app itself never does - it only reads the generated file.

The download is about 1.5 GB compressed, so the file is streamed and decompressed
as it arrives rather than held in memory. Expect several minutes.

What this covers and what it does not: Redfin publishes *sale* data. It has no
rent figures at all, so median_rent_estimate still comes from market_data.json or
its fallbacks. What Redfin adds is what the property is worth and which way the
market is moving - median sale price, year-over-year change, days on market,
months of supply, and sale-to-list ratio.

Data source: https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz
Data center: https://www.redfin.com/news/data-center/
License: free to use with attribution to Redfin. The generated records carry a
source_label naming Redfin so every number in the report stays traceable.
"""

from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SOURCE_URL = (
    "https://redfin-public-data.s3.us-west-2.amazonaws.com"
    "/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"
)
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "redfin_markets.json"

# Redfin repeats every ZIP once per property type. "All Residential" is the
# combined row; taking it avoids counting the same sales several times over.
WANTED_PROPERTY_TYPE = "All Residential"

# The file reaches back to 2012, and a few thousand thin ZIPs have not recorded
# a sale in years. A stale median is worse than no median: it would drive the
# "above market price" check and the final recommendation off numbers a decade
# old. Those ZIPs are dropped so the app falls back to sample data and says so.
MAX_AGE_DAYS = 730

# Only the columns the report can actually use. Redfin ships 58.
FIELDS = {
    "median_sale_price": "MEDIAN_SALE_PRICE",
    "median_sale_price_yoy": "MEDIAN_SALE_PRICE_YOY",
    "median_list_price": "MEDIAN_LIST_PRICE",
    "median_ppsf": "MEDIAN_PPSF",
    "homes_sold": "HOMES_SOLD",
    "inventory": "INVENTORY",
    "months_of_supply": "MONTHS_OF_SUPPLY",
    "median_days_on_market": "MEDIAN_DOM",
    "avg_sale_to_list": "AVG_SALE_TO_LIST",
}


def _clean(value: str) -> str:
    """Redfin quotes text fields and writes NA for missing numbers."""
    value = value.strip().strip('"')
    return "" if value in {"NA", "N/A"} else value


def _number(value: str) -> float | None:
    value = _clean(value)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _zip_from_region(region: str) -> str:
    """Turn Redfin's "Zip Code: 60616" into "60616"."""
    region = _clean(region)
    _, _, zip_code = region.partition(":")
    zip_code = zip_code.strip()
    return zip_code if zip_code.isdigit() and len(zip_code) == 5 else ""


def build() -> dict[str, dict[str, Any]]:
    print(f"Streaming {SOURCE_URL} ...")
    print("  about 1.5 GB compressed - this takes a few minutes")

    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "NorthStar/1.0"})
    markets: dict[str, dict[str, Any]] = {}
    rows = 0

    with urllib.request.urlopen(request, timeout=300) as response:
        with gzip.GzipFile(fileobj=response) as stream:
            header = stream.readline().decode("utf-8").rstrip("\n").split("\t")
            index = {_clean(name): position for position, name in enumerate(header)}

            for raw in stream:
                rows += 1
                if rows % 1_000_000 == 0:
                    print(f"  {rows:,} rows read, {len(markets):,} ZIPs kept")

                fields = raw.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(fields) < len(header):
                    continue
                if _clean(fields[index["PROPERTY_TYPE"]]) != WANTED_PROPERTY_TYPE:
                    continue

                zip_code = _zip_from_region(fields[index["REGION"]])
                if not zip_code:
                    continue

                period_end = _clean(fields[index["PERIOD_END"]])
                existing = markets.get(zip_code)
                # The file holds every period back to 2012. Keep only the newest
                # row per ZIP; rows are not guaranteed to arrive in date order.
                if existing and existing["period_end"] >= period_end:
                    continue

                record = {
                    "period_end": period_end,
                    "city": _clean(fields[index["CITY"]]),
                    "state_code": _clean(fields[index["STATE_CODE"]]),
                    "metro": _clean(fields[index["PARENT_METRO_REGION"]]),
                }
                for name, column in FIELDS.items():
                    record[name] = _number(fields[index[column]])

                if record["median_sale_price"] is None:
                    # A row with no sale price tells the investor nothing.
                    continue
                markets[zip_code] = record

    print(f"  {rows:,} rows read, {len(markets):,} ZIPs with sale data")

    cutoff = (date.today() - timedelta(days=MAX_AGE_DAYS)).isoformat()
    fresh = {
        zip_code: record
        for zip_code, record in markets.items()
        if record["period_end"] >= cutoff
    }
    print(f"  {len(markets) - len(fresh):,} dropped as stale (no sale since {cutoff})")
    print(f"  {len(fresh):,} ZIPs kept")
    return fresh


def main() -> int:
    markets = build()
    if len(markets) < 1000:
        print(
            f"Only {len(markets)} ZIPs parsed - that is too few to be right. "
            "The source layout may have changed; data/redfin_markets.json was left alone.",
            file=sys.stderr,
        )
        return 1

    payload = {
        "source_label": "Redfin Data Center, ZIP-level market tracker",
        "source_url": "https://www.redfin.com/news/data-center/",
        "retrieval_date": date.today().isoformat(),
        "zip_markets": dict(sorted(markets.items())),
    }
    OUTPUT.write_text(json.dumps(payload, indent=1, sort_keys=False), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1_048_576:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
