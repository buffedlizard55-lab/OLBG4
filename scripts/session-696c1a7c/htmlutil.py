"""Minimal HTML table reader for the governing-body pages in this capture.

The pages we read are either JSON APIs or plain server-rendered tables. This
module converts a `<table>` into a list of rows of cell text so a parser can be
written against the numbers rather than against markup, and strips the tags /
entities that would otherwise leak into published text.

No network access, no external dependencies.
"""
from __future__ import annotations

import html
import re

TAG = re.compile(r"<[^>]+>")
CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
TABLE = re.compile(r"<table\b.*?</table>", re.S | re.I)
SPACE = re.compile(r"\s+")


def text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = TAG.sub(" ", fragment)
    fragment = html.unescape(fragment)
    fragment = fragment.replace("\xa0", " ")
    return SPACE.sub(" ", fragment).strip()


def tables(page: str) -> list[list[list[str]]]:
    out = []
    for t in TABLE.findall(page):
        rows = []
        for r in ROW.findall(t):
            cells = [text(c) for c in CELL.findall(r)]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def table_by_header(page: str, *needles: str) -> list[list[str]] | None:
    """First table whose header cells contain every needle (case-insensitive)."""
    for table in tables(page):
        head = " ".join(table[0]).lower()
        if all(n.lower() in head for n in needles):
            return table
    return None


def to_int(value: str) -> int | None:
    value = (value or "").strip().replace(" ", "")
    if not value:
        return None
    m = re.match(r"^-?\d+$", value)
    return int(m.group(0)) if m else None


def to_float(value: str) -> float | None:
    value = (value or "").strip().replace("%", "").replace(",", ".").replace(" ", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
