
"""NSE PIT XBRL parser.

The parser is deliberately schema-tolerant. NSE PIT filings can expose
transaction fields under different element names and nesting patterns.
We return one dictionary per disclosure and preserve the raw fields.
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


def leaf_fields(element: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in element.iter():
        if child is element or len(list(child)) != 0:
            continue
        value = text(child)
        if value is not None:
            result[local_name(child.tag)] = value
    return result


def _disclosure_groups(root: ET.Element) -> list[dict[str, Any]]:
    groups = []
    for element in root.iter():
        name = local_name(element.tag)
        if re.fullmatch(r"Disclosure\d+", name, re.IGNORECASE):
            fields = leaf_fields(element)
            if fields:
                groups.append(fields)
    return groups


def _contexts(root: ET.Element) -> dict[str, dict[str, str]]:
    """Read XBRL contexts into a compact context-id -> metadata mapping."""
    contexts: dict[str, dict[str, str]] = {}

    for element in root.iter():
        if local_name(element.tag).lower() != "context":
            continue

        context_id = element.attrib.get("id")
        if not context_id:
            continue

        fields = {}
        for child in element.iter():
            if child is element:
                continue
            value = text(child)
            if value:
                fields[local_name(child.tag)] = value

        contexts[context_id] = fields

    return contexts


def _context_grouped_facts(root: ET.Element) -> list[dict[str, Any]]:
    """Group flat XBRL leaf facts by their Disclosure contextRef.

    NSE PIT filings do NOT wrap disclosures in DisclosureN XML elements.
    Instead, every leaf fact carries a contextRef attribute like
    contextRef="Disclosure1". This function splits those facts into one
    dict per Disclosure context and merges header facts (MainI etc.) into
    each, producing the same shape that _disclosure_groups would return for
    filings that do use wrapper elements.
    """
    from collections import defaultdict

    disclosure_groups: dict[str, dict[str, str]] = defaultdict(dict)
    header: dict[str, str] = {}

    for element in root.iter():
        if len(list(element)) != 0:
            continue

        value = text(element)
        if value is None:
            continue

        field = local_name(element.tag)
        ctx = element.attrib.get("contextRef", "")

        if re.fullmatch(r"Disclosure\d+", ctx, re.IGNORECASE):
            # Only keep the first value for a field within a context
            # (identical to how _disclosure_groups / leaf_fields behaves).
            disclosure_groups[ctx].setdefault(field, value)
        else:
            header.setdefault(field, value)

    if not disclosure_groups:
        return []

    # Merge header fields into each disclosure, disclosure fields win.
    result = []
    for ctx in sorted(disclosure_groups, key=lambda k: int(re.search(r"\d+", k).group())):
        record = dict(header)
        record.update(disclosure_groups[ctx])
        result.append(record)

    return result


def _flat_facts(root: ET.Element) -> list[dict[str, Any]]:
    """Last-resort fallback for filings with no recognisable structure.

    Keep all leaf facts with their contextRef so the normalizer can still
    attempt to identify values even when element names are non-standard.
    """
    facts = []
    for element in root.iter():
        if len(list(element)) != 0:
            continue

        value = text(element)
        if value is None:
            continue

        facts.append({
            "field": local_name(element.tag),
            "value": value,
            "contextRef": element.attrib.get("contextRef"),
            "unitRef": element.attrib.get("unitRef"),
            "decimals": element.attrib.get("decimals"),
        })

    return facts


def parse_xbrl(xml_path: str | Path) -> list[dict[str, Any]]:
    root = ET.parse(xml_path).getroot()

    # 1. Try filings that use explicit <Disclosure1> wrapper elements.
    grouped = _disclosure_groups(root)
    if grouped:
        return grouped

    # 2. Try the NSE/BSE flat format where disclosures are identified by
    #    contextRef="Disclosure1" attributes on individual leaf facts.
    ctx_grouped = _context_grouped_facts(root)
    if ctx_grouped:
        return ctx_grouped

    # 3. Last resort: return a single record containing everything, plus the
    #    full facts list so the normalizer can still attempt extraction.
    facts = _flat_facts(root)
    contexts = _contexts(root)

    record: dict[str, Any] = {
        "_facts": facts,
        "_contexts": contexts,
    }

    for fact in facts:
        # Keep the first value under its field name.
        record.setdefault(fact["field"], fact["value"])

    return [record] if facts else []
