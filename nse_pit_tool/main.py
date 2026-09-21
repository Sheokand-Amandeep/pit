
"""NSE PIT application entry point.

No arguments = fetch the complete dataset currently exposed by NSE.
Optional dates = fetch only a selected date range.
"""

from __future__ import annotations

import argparse
from datetime import datetime, date
from pathlib import Path
import shutil

from config import CACHE_DIR
from nse_client import NSEClient
from downloader import download_xml_files
from xml_parser import parse_xbrl
from normalizer import normalize
from exporter import export
from progress import ProgressBar


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use DD-MM-YYYY."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and present NSE PIT insider-trading disclosures."
    )
    parser.add_argument("--from-date", type=parse_date)
    parser.add_argument("--to-date", type=parse_date)
    parser.add_argument("--clear-cache", action="store_true")
    args = parser.parse_args()

    if (args.from_date is None) != (args.to_date is None):
        raise SystemExit("Use both --from-date and --to-date, or neither.")

    if args.from_date and args.from_date > args.to_date:
        raise SystemExit("--from-date cannot be after --to-date.")

    if args.clear_cache and CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("\nNSE PIT DISCLOSURE TOOL")
    print("=" * 42)

    client = NSEClient()

    if args.from_date:
        print(f"Date range: {args.from_date:%d-%m-%Y} → {args.to_date:%d-%m-%Y}")
        records = client.get_pit_filings(args.from_date, args.to_date)
    else:
        print("Date range: ALL DATA AVAILABLE FROM NSE")
        # The API has proven to return the full current dataset when no dates
        # are supplied. Keep this behavior explicit and easy to change.
        records = client.get_pit_filings_without_dates()

    print(f"Filings found: {len(records):,}")

    if not records:
        print("No PIT filings found.")
        return

    print("\nDownloading XML files...")
    xml_paths = download_xml_files(records, CACHE_DIR)
    print(f"XML files available: {len(xml_paths):,}")

    rows = []
    failures = []

    print("\nParsing disclosures...")
    progress = ProgressBar(len(records), "Parsing")

    for i, api_record in enumerate(records, 1):
        url = api_record.get("xmlFileName")
        path = xml_paths.get(url)

        try:
            if not path:
                raise RuntimeError("XML file was not available.")

            disclosures = parse_xbrl(path)
            if not disclosures:
                raise RuntimeError("No disclosure fields found in XML.")

            for disclosure in disclosures:
                rows.append(normalize(api_record, disclosure))

        except Exception as exc:
            failures.append((api_record.get("appId"), str(exc)))

        company = str(api_record.get("symbol") or api_record.get("companyName") or "")
        progress.update(i, company)

    excel_path, csv_path = export(rows)

    print("\n" + "=" * 42)
    print("COMPLETE")
    print("=" * 42)
    print(f"Filing rows received : {len(records):,}")
    print(f"Disclosure rows      : {len(rows):,}")
    print(f"Failed filings       : {len(failures):,}")
    print(f"Excel                : {excel_path}")
    print(f"CSV                  : {csv_path}")

    if failures:
        print("\nFirst failures:")
        for app_id, reason in failures[:10]:
            print(f"  {app_id}: {reason}")


if __name__ == "__main__":
    main()
