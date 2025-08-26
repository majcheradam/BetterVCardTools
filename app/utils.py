from __future__ import annotations

import re
from collections.abc import Iterable

CRLF = "\r\n"


def escape_text(s: object) -> str:
    """Escape text for vCard value context according to RFC 6350 basics.

    Escapes backslashes, commas, semicolons, and newlines. Removes stray CR.
    """
    if s is None:
        return ""
    value = str(s)
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\\;")
        .replace(",", r"\\,")
        .replace("\n", r"\\n")
        .replace("\r", "")
    )


def split_types(val: object) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        parts = [p.strip() for p in val.split(",") if p.strip()]
    elif isinstance(val, list):
        parts = []
        for x in val:
            parts.extend([p.strip() for p in str(x).split(",") if p.strip()])
    else:
        parts = [str(val).strip()]
    return [p.lower() for p in parts]


def normalize_types(kind: str, types: Iterable[str]) -> list[str]:
    tset = set([t.lower() for t in (types or [])])
    if kind == "email":
        tset.discard("internet")
    if kind == "tel" and len(tset) > 1 and "voice" in tset:
        tset.remove("voice")
    return sorted(tset)


KNOWN_TEL_TYPES = {
    "home",
    "work",
    "cell",
    "voice",
    "fax",
    "pager",
    "text",
    "textphone",
    "main",
    "iphone",
}

KNOWN_EMAIL_TYPES = {"home", "work", "internet", "pref", "x-mobileme"}


def extract_types_from_params(kind: str, params: dict, singletonparams) -> list[str]:
    types: list[str] = []
    p = params or {}
    if "TYPE" in p:
        types.extend(split_types(p.get("TYPE")))
    for key, _val in p.items():
        k = str(key).lower()
        if k == "type":
            continue
        if kind == "tel" and k in KNOWN_TEL_TYPES:
            types.append(k)
        if kind == "email" and k in KNOWN_EMAIL_TYPES:
            types.append(k)
    if singletonparams:
        types.extend(split_types(singletonparams))
    return normalize_types(kind, types)


def normalize_tel_uri(raw: str) -> str:
    tel_raw = str(raw or "")
    tel = re.sub(r"[\s()\-.]", "", tel_raw)
    if not tel.startswith("tel:"):
        tel = f"tel:{tel}"
    return tel


__all__ = [
    "CRLF",
    "escape_text",
    "split_types",
    "normalize_types",
    "extract_types_from_params",
    "normalize_tel_uri",
    "KNOWN_TEL_TYPES",
    "KNOWN_EMAIL_TYPES",
]
