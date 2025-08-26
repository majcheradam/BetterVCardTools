import re
from typing import Optional
from uuid import uuid4

import vobject

from .models import Contact, Email, Name, Phone

CRLF = "\r\n"


def _escape(s: str) -> str:
    if not s:
        return ""
    return (
        str(s)
        .replace("\\", "\\\\")
        .replace(";", r"\\;")
        .replace(",", r"\\,")
        .replace("\n", r"\\n")
        .replace("\r", "")
    )


_PREFIXES = {"mr", "mrs", "ms", "dr", "prof"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}


def _split_name(fn: str) -> Name:
    """Best-effort split of a display name into structured N fields."""
    tokens = [t for t in re.split(r"\s+", (fn or "").strip()) if t]
    if not tokens:
        return Name()

    def norm(t: str) -> str:
        return re.sub(r"\.+$", "", t).lower()

    prefix = tokens[0] if norm(tokens[0]) in _PREFIXES else ""
    suffix = tokens[-1] if norm(tokens[-1]) in _SUFFIXES else ""
    core = (
        tokens[1:-1]
        if (prefix and suffix)
        else (tokens[1:] if prefix else (tokens[:-1] if suffix else tokens))
    )
    if not core:
        return Name(
            family="",
            given=tokens[0] if tokens else "",
            additional="",
            prefix=prefix,
            suffix=suffix,
        )
    if len(core) == 1:
        given, family = core[0], ""
    else:
        given, family = core[0], " ".join(core[1:])
    return Name(family=family, given=given, additional="", prefix=prefix, suffix=suffix)


def _split_types(val) -> list[str]:
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


def _normalize_types(kind: str, types: list[str]) -> list[str]:
    tset = set(types or [])
    if kind == "email":
        tset.discard("internet")
    if kind == "tel" and len(tset) > 1 and "voice" in tset:
        tset.remove("voice")
    return sorted(tset)


_KNOWN_TEL_TYPES = {
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
_KNOWN_EMAIL_TYPES = {"home", "work", "internet", "pref", "x-mobileme"}


def _extract_types_from_params(kind: str, params: dict, singletonparams) -> list[str]:
    types: list[str] = []
    p = params or {}
    if "TYPE" in p:
        types.extend(_split_types(p.get("TYPE")))
    for key, _val in p.items():
        k = str(key).lower()
        if k == "type":
            continue
        if kind == "tel" and k in _KNOWN_TEL_TYPES:
            types.append(k)
        if kind == "email" and k in _KNOWN_EMAIL_TYPES:
            types.append(k)
    if singletonparams:
        types.extend(_split_types(singletonparams))
    return _normalize_types(kind, types)


essential_fields = ("fn", "email_list", "tel_list", "org")


def parse_vcards(text: str) -> list[Contact]:
    """Parse vCard text into a list of Contact dataclasses."""
    contacts: list[Contact] = []
    for v in vobject.readComponents(text):
        fn_obj = getattr(v, "fn", None)
        fn_val: Optional[str] = fn_obj.value if fn_obj is not None else None
        n_struct: Optional[Name] = None
        n_obj = getattr(v, "n", None)
        if n_obj is not None:
            nval = n_obj.value
            n_struct = Name(
                family=nval.family or "",
                given=nval.given or "",
                additional=nval.additional or "",
                prefix=nval.prefix or "",
                suffix=nval.suffix or "",
            )
        elif fn_val:
            n_struct = _split_name(str(fn_val))

        emails: list[Email] = []
        for e in getattr(v, "email_list", []):
            params = getattr(e, "params", {}) or {}
            singleton = getattr(e, "singletonparams", []) or []
            types = _extract_types_from_params("email", params, singleton)
            emails.append(Email(value=e.value, types=types))

        phones: list[Phone] = []
        for p in getattr(v, "tel_list", []):
            params = getattr(p, "params", {}) or {}
            singleton = getattr(p, "singletonparams", []) or []
            types = _extract_types_from_params("tel", params, singleton)
            phones.append(Phone(value=p.value, types=types))

        org_list = None
        org_obj = getattr(v, "org", None)
        if org_obj is not None:
            try:
                vals = org_obj.value or []
                org_list = [str(x) for x in vals]
            except Exception:
                try:
                    org_list = [str(org_obj.value)]
                except Exception:
                    org_list = None

        contacts.append(Contact(name=fn_val, n=n_struct, emails=emails, phones=phones, org=org_list))
    return contacts


def contact_to_vcard40(c: Contact) -> str:
    props = ["BEGIN:VCARD", "VERSION:4.0"]
    name = c.name or "Unnamed"
    n_struct = c.n or Name(given=name)
    n_fields = [
        _escape(n_struct.family),
        _escape(n_struct.given),
        _escape(n_struct.additional),
        _escape(n_struct.prefix),
        _escape(n_struct.suffix),
    ]
    props.append("N:" + ";".join(n_fields))
    props.append(f"FN:{_escape(name)}")

    for e in c.emails:
        types = _normalize_types("email", e.types)
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"EMAIL{type_param}:{_escape(e.value)}")

    for p in c.phones:
        tel_raw = str(p.value)
        tel = re.sub(r"[\s()\-.]", "", tel_raw)
        if not tel.startswith("tel:"):
            tel = f"tel:{tel}"
        types = _normalize_types("tel", p.types)
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"TEL{type_param};VALUE=uri:{_escape(tel)}")

    if c.org:
        comps = [_escape(str(comp)) for comp in c.org or []]
        props.append("ORG:" + ";".join(comps))

    props.append("PRODID:-//BetterVCardTools//v1.0//EN")
    props.append(f"UID:urn:uuid:{uuid4()}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: list[Contact]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)

