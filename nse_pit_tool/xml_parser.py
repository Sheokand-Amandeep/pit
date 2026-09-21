"""NSE PIT XBRL parser.

NSE PIT V2.0 XBRL filings store the company-level facts in the ``MainI``
context and each actual disclosure in a separate XBRL context such as
``Disclosure1``, ``Disclosure2``, etc.  This parser groups facts by their
contextRef rather than looking for literal <Disclosure1> XML elements.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import xml.etree.ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    value = "".join(element.itertext()).strip()
    return value or None


def _leaf_facts(root: ET.Element) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for element in root.iter():
        # XBRL facts are leaf elements. Ignore schemaRef and other structural nodes.
        if len(list(element)) != 0:
            continue
        value = text(element)
        if value is None:
            continue
        context_ref = element.attrib.get("contextRef")
        if not context_ref:
            continue
        facts.append({
            "field": local_name(element.tag),
            "value": value,
            "contextRef": context_ref,
            "unitRef": element.attrib.get("unitRef"),
            "decimals": element.attrib.get("decimals"),
        })
    return facts


def _is_disclosure_context(context_ref: str) -> bool:
    return bool(re.fullmatch(r"Disclosure\d+", context_ref or "", re.IGNORECASE))


def parse_xbrl(xml_path: str | Path) -> list[dict[str, Any]]:
    root = ET.parse(xml_path).getroot()
    facts = _leaf_facts(root)
    if not facts:
        return []

    # Company/document-level facts live in MainI.  Transaction/disclosure facts
    # live in Disclosure1, Disclosure2, ... .
    main_fields: dict[str, Any] = {}
    disclosure_fields: dict[str, dict[str, Any]] = {}

    for fact in facts:
        field = fact["field"]
        value = fact["value"]
        context_ref = fact.get("contextRef") or ""

        if _is_disclosure_context(context_ref):
            disclosure_fields.setdefault(context_ref, {})[field] = value
        elif context_ref == "MainI":
            main_fields[field] = value

    # Normal NSE PIT V2.0 filings use one DisclosureN context per disclosure.
    # Sort numerically so Disclosure10 follows Disclosure9 rather than Disclosure1.
    def disclosure_number(name: str) -> int:
        m = re.search(r"(\\d+)$", name)
        return int(m.group(1)) if m else 0

    records: list[dict[str, Any]] = []
    for context_ref in sorted(disclosure_fields, key=disclosure_number):
        record = dict(main_fields)
        record.update(disclosure_fields[context_ref])
        record["_contextRef"] = context_ref
        record["_raw_facts"] = [f for f in facts if f.get("contextRef") in ("MainI", context_ref)]
        records.append(record)

    # Fallback for unusual XBRL files that do not use DisclosureN contexts.
    if not records:
        record = dict(main_fields)
        for fact in facts:
            record.setdefault(fact["field"], fact["value"])
        record["_raw_facts"] = facts
        records.append(record)

    return records
