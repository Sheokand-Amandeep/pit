"""Convert NSE PIT XBRL disclosure records into human-readable rows."""

from __future__ import annotations
from typing import Any
import json


def numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        s = str(value).replace(",", "").replace("₹", "").strip()
        return float(s)
    except (TypeError, ValueError):
        return None


def human_action(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    low = s.lower()
    if low in {"buy", "purchase", "bought", "acquisition"}:
        return "Buy"
    if low in {"sell", "sale", "sold", "disposal"}:
        return "Sell"
    return s


def normalize(api: dict[str, Any], xml: dict[str, Any]) -> dict[str, Any]:
    # These names are the actual PIT V2.0 element names visible in the supplied
    # NSE/BSE XBRL files. Do not infer a price-per-share field: the XML supplies
    # value of securities, not a market price field.
    shares = numeric(xml.get("SecuritiesAcquiredOrDisposedNumberOfSecurity"))
    value = numeric(xml.get("SecuritiesAcquiredOrDisposedValueOfSecurity"))
    before = numeric(xml.get("SecuritiesHeldPriorToAcquisitionOrDisposalNumberOfSecurity"))
    before_pct = numeric(xml.get("SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding"))
    after = numeric(xml.get("SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity"))
    after_pct = numeric(xml.get("SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding"))

    raw_fields = {
        k: v for k, v in xml.items()
        if not str(k).startswith("_") and k not in {
            "ScripCode", "Symbol", "NameOfTheCompany", "DateOfFiling",
            "DisclosureUnderRegulation", "RevisedFilling", "TypeOfInstrument",
            "CategoryOfPerson", "NameOfThePerson", "SecuritiesHeldPriorToAcquisitionOrDisposalNumberOfSecurity",
            "SecuritiesHeldPriorToAcquisitionOrDisposalPercentageOfShareholding",
            "SecuritiesAcquiredOrDisposedNumberOfSecurity", "SecuritiesAcquiredOrDisposedValueOfSecurity",
            "SecuritiesAcquiredOrDisposedTransactionType", "SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity",
            "SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding",
            "DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate",
            "DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyToDate",
            "ModeOfAcquisitionOrDisposal", "DateOfIntimationToCompany", "ExchangeOnWhichTheTradeWasExecuted",
        }
    }

    return {
        "Disclosure Date": api.get("broadcastDateTime"),
        "Company": api.get("companyName") or xml.get("NameOfTheCompany"),
        "Symbol": api.get("symbol") or xml.get("Symbol"),
        "Person": xml.get("NameOfThePerson"),
        "Category": xml.get("CategoryOfPerson"),
        "Action": human_action(xml.get("SecuritiesAcquiredOrDisposedTransactionType")),
        "Shares": shares,
        "Transaction Value": value,
        "Transaction Date": xml.get("DateOfAllotmentAdviceOrAcquisitionOfSharesOrSaleOfSharesSpecifyFromDate"),
        "Mode": xml.get("ModeOfAcquisitionOrDisposal"),
        "Exchange": xml.get("ExchangeOnWhichTheTradeWasExecuted"),
        "Shares Before": before,
        "Holding % Before": before_pct,
        "Shares After": after,
        "Holding % After": after_pct,
        "Submission": api.get("typeOfSubmission"),
        "Revision Reason": api.get("revisionRemark"),
        "App ID": api.get("appId"),
        "Previous App ID": api.get("prevAppId"),
        "NSE XML URL": api.get("xmlFileName"),
        "NSE iXBRL URL": api.get("ixbrl"),
        "_Raw XML Fields": json.dumps(raw_fields, ensure_ascii=False),
    }
