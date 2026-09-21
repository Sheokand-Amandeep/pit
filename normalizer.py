
"""Convert raw NSE API + XBRL information into human-readable PIT rows."""

from __future__ import annotations
from typing import Any
import json
import re


ALIASES = {
    "Scrip Code": [
        "ScripCode", "Scrip_Code", "Scripcode"
    ],
    "Person": [
        "NameOfThePerson", "NameOfPerson", "PersonName", "NameOfThePersonDesignatedPerson"
    ],
    "Category": [
        "CategoryOfPerson", "Category", "PersonCategory"
    ],
    "Shares Before": [
        "NoOfSharesHeldBeforeAcquisitionOrDisposal",
        "NoOfSharesBeforeAcquisitionOrDisposal",
        "PreHolding", "SharesBefore", "NoOfSharesHeldBefore",
        # NSE/BSE XBRL flat format
        "SecuritiesHeldPriorToAcquisitionOrDisposalNumberOfSecurity",
    ],
    "Holding % Before": [
        "PercentageOfShareholdingBeforeAcquisitionOrDisposal",
        "PreHoldingPercentage", "HoldingPercentageBefore",
        "PercentageHoldingBefore", "PercentHoldingBefore",
        # NSE/BSE XBRL flat format
        "SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding",
    ],
    "Shares Acquired / Disposed": [
        "NoOfSharesAcquiredDisposed",
        "NoOfSharesAcquiredOrDisposed",
        "NoOfSharesAcquiredDisposedOf",
        "SharesAcquiredDisposed",
        "NumberOfSharesAcquiredDisposed",
        "NoOfSharesAcquiredDisposedDuringThePeriod",
        # NSE/BSE XBRL flat format
        "SecuritiesAcquiredOrDisposedNumberOfSecurity",
    ],
    "Holding % Acquired / Disposed": [
        "PercentageOfSharesAcquiredDisposed",
        "PercentageOfShareholdingAcquiredDisposed",
        "HoldingPercentageAcquiredDisposed",
        # NSE/BSE XBRL flat format
        "SecuritiesAcquiredOrDisposedPercentageOfShareholding",
    ],
    "Shares After": [
        "NoOfSharesHeldAfterAcquisitionOrDisposal",
        "NoOfSharesAfterAcquisitionOrDisposal",
        "PostHolding", "SharesAfter", "NoOfSharesHeldAfter",
        # NSE/BSE XBRL flat format (note: NSE XML has a typo: PostAcquistion)
        "SecuritiesHeldPostAcquisitionOrDisposalNumberOfSecurity",
        "SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity",
    ],
    "Holding % After": [
        "PercentageOfShareholdingAfterAcquisitionOrDisposal",
        "PostHoldingPercentage", "HoldingPercentageAfter",
        "PercentageHoldingAfter", "PercentHoldingAfter",
        # NSE/BSE XBRL flat format (note: NSE XML has a typo: PostAcquistion)
        "SecuritiesHeldPostAcquisitionOrDisposalPercentageOfShareholding",
        "SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding",
    ],
    "Price Per Share": [
        "PricePerShare", "PriceOfSecurity", "PricePerSecurity",
        "TradePrice", "AveragePrice", "Price", "RatePerShare",
        "PriceOfEachSecurity", "ValuePerShare", "AcquisitionPrice",
        "DisposalPrice", "MarketPrice", "ConsiderationPerShare"
    ],
    "Transaction Value": [
        "ValueOfTransaction", "TransactionValue",
        "ValueOfSecuritiesTransacted", "TransactionAmount",
        "TotalTransactionValue", "ValueOfSecurities",
        # NSE/BSE XBRL flat format
        "SecuritiesAcquiredOrDisposedValueOfSecurity",
    ],
    "Transaction Type": [
        "TypeOfTransaction", "TransactionType", "BuySell",
        "NatureOfTransaction", "TypeOfSecurityTransaction",
        "TransactionTypeBuySell",
        # NSE/BSE XBRL flat format
        "SecuritiesAcquiredOrDisposedTransactionType",
    ],
    "Transaction Date": [
        "DateOfAcquisitionOrDisposal", "DateOfTransaction",
        "TransactionDate", "DateOfTrade",
        # NSE/BSE XBRL flat format (from-date is used as the transaction date)
        "DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate",
    ],
    "Mode": [
        "ModeOfAcquisitionOrDisposal", "ModeOfAcquisitionDisposal",
        "ModeOfAcquisition", "ModeOfDisposal", "ModeOfTransaction"
    ],
    "Intimation Date": [
        "DateOfIntimationToCompany", "DateOfIntimation",
        "DateOfIntimationToStockExchange"
    ],
    "Exchange": [
        "ExchangeOnWhichTheTradeWasExecuted", "Exchange",
        "NameOfStockExchange"
    ],
}


def _clean_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _all_values(record: dict[str, Any]):
    """Yield field/value pairs from both ordinary fields and flat XBRL facts."""
    for key, value in record.items():
        if not str(key).startswith("_"):
            yield str(key), value

    for fact in record.get("_facts", []) or []:
        if isinstance(fact, dict):
            yield str(fact.get("field", "")), fact.get("value")


def lookup(record: dict[str, Any], aliases: list[str]) -> Any:
    wanted = {_clean_key(a) for a in aliases}

    for key, value in _all_values(record):
        if _clean_key(key) in wanted and value not in (None, ""):
            return value

    return None


def numeric(value: Any) -> float | None:
    if value is None:
        return None

    # Remove commas, currency symbols, spaces and common accounting text.
    s = str(value).replace(",", "").replace("₹", "").strip()
    s = re.sub(r"[^\d.\-]", "", s)

    if not s or s in {"-", "."}:
        return None

    try:
        return float(s)
    except ValueError:
        return None


def price_from_value(value: Any, shares: Any) -> float | None:
    total = numeric(value)
    count = numeric(shares)
    if total is None or count in (None, 0):
        return None
    return total / count


def human_action(value: Any) -> str | None:
    if value is None:
        return None

    s = str(value).strip()
    low = s.lower()

    if any(x in low for x in ("purchase", "buy", "bought", "acquisition")):
        return "Buy"
    if any(x in low for x in ("sale", "sell", "sold", "disposal")):
        return "Sell"
    return s


def _derived_price(xml: dict[str, Any], value: Any, shares: Any) -> Any:
    # Explicit price is preferred.
    explicit = lookup(xml, ALIASES["Price Per Share"])
    if explicit not in (None, ""):
        return explicit

    # Otherwise derive it from total transaction value / shares.
    return price_from_value(value, shares)


def normalize(api: dict[str, Any], xml: dict[str, Any]) -> dict[str, Any]:
    shares = lookup(xml, ALIASES["Shares Acquired / Disposed"])
    value = lookup(xml, ALIASES["Transaction Value"])

    known_xml_keys = {
        _clean_key(alias)
        for aliases in ALIASES.values()
        for alias in aliases
    }

    raw_fields = {}
    for key, val in xml.items():
        if str(key).startswith("_"):
            continue
        if _clean_key(key) not in known_xml_keys:
            raw_fields[key] = val

    return {
        "Disclosure Date": api.get("broadcastDateTime"),
        "Company": api.get("companyName"),
        "Symbol": api.get("symbol"),
        "Person": lookup(xml, ALIASES["Person"]),
        "Category": lookup(xml, ALIASES["Category"]),
        "Action": human_action(lookup(xml, ALIASES["Transaction Type"])),
        "Shares": shares,
        "Price Per Share": _derived_price(xml, value, shares),
        "Transaction Value": value,
        "Transaction Date": lookup(xml, ALIASES["Transaction Date"]),
        "Mode": lookup(xml, ALIASES["Mode"]),
        "Exchange": lookup(xml, ALIASES["Exchange"]),
        "Shares Before": lookup(xml, ALIASES["Shares Before"]),
        "Holding % Before": lookup(xml, ALIASES["Holding % Before"]),
        "Shares After": lookup(xml, ALIASES["Shares After"]),
        "Holding % After": lookup(xml, ALIASES["Holding % After"]),
        "Submission": api.get("typeOfSubmission"),
        "Revision Reason": api.get("revisionRemark"),
        "App ID": api.get("appId"),
        "Previous App ID": api.get("prevAppId"),
        "NSE XML URL": api.get("xmlFileName"),
        "NSE iXBRL URL": api.get("ixbrl"),
        "_Raw XML Fields": json.dumps(raw_fields, ensure_ascii=False),
    }
