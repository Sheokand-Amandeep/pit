
# NSE PIT Disclosure Tool

A maintainable Python application that converts NSE Insider Trading / PIT
filings into a clean, human-readable Excel/CSV dataset.

## Run the complete current NSE dataset

Simply:

```bash
python main.py
```

This uses the NSE PIT API without date filters and processes all rows returned
by NSE.

## Run a date range

```bash
python main.py --from-date 01-09-2026 --to-date 21-09-2026
```

## Re-download XML files

```bash
python main.py --clear-cache
```

## Main output

`output/NSE_PIT_Disclosures.xlsx`

The main sheet is designed for a normal user and contains:

- Company
- Symbol
- Person
- Category
- Buy/Sell
- Shares
- Price per share
- Transaction value
- Transaction date
- Mode
- Exchange
- Holdings before/after
- Original/Revision
- Revision reason

Technical URLs and raw fields remain in a separate Source Details sheet.

## Pricing logic

1. An explicit XBRL price-per-share field is used when present.
2. If NSE does not provide an explicit price field, the tool calculates:

   Transaction Value / Shares

The parser checks several known NSE field spellings instead of relying on
one exact XML tag name.

## Progress display

The terminal shows:

- percentage
- processed / total
- estimated remaining time
- elapsed time
- current symbol

## Project structure

- `main.py` — orchestration and command-line behavior
- `config.py` — settings
- `nse_client.py` — NSE API
- `downloader.py` — XML download/cache
- `xml_parser.py` — XBRL extraction
- `normalizer.py` — business-friendly PIT fields and pricing
- `progress.py` — terminal progress bar
- `exporter.py` — Excel/CSV formatting


### XBRL mapping note
NSE/BSE PIT V2.0 files use `MainI` for company-level facts and `Disclosure1`, `Disclosure2`, etc. as XBRL `contextRef` values for each disclosure. The parser groups facts by those contextRef values. `SecuritiesAcquiredOrDisposedValueOfSecurity` is retained as Transaction Value; it is not treated as a share price.
