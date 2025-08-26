from __future__ import annotations

import re
from uuid import uuid4

import vobject

from .types import Contact, EmailEntry, NameStruct, PhoneEntry
from .utils import (
    CRLF,
    escape_text,
    extract_types_from_params,
    normalize_tel_uri,
    normalize_types,
)

_PREFIXES = {"mr", "mrs", "ms", "dr", "prof"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}

def _split_name(fn: str) -> NameStruct:
    """Best-effort split of a display name into structured N fields.
    Returns dict with keys: family, given, additional, prefix, suffix.
    """
    tokens = [t for t in re.split(r"\s+", (fn or "").strip()) if t]
    if not tokens:
        return {"family": "", "given": "", "additional": "", "prefix": "", "suffix": ""}
    # Normalize helper strips trailing dots for prefix/suffix matching
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
        return {
            "family": "",
            "given": tokens[0] if tokens else "",
            "additional": "",
            "prefix": prefix,
            "suffix": suffix,
        }
    if len(core) == 1:
        given, family = core[0], ""
        additional = ""
    else:
        given, family = core[0], " ".join(core[1:])
        additional = ""
    return {
        "family": family,
        "given": given,
        "additional": additional,
        "prefix": prefix,
        "suffix": suffix,
    }

_KNOWN_TEL_TYPES = {
    "home", "work", "cell", "voice", "fax", "pager", "text", "textphone", "main", "iphone"
}

essential_fields = ("fn", "email_list", "tel_list", "org")

def parse_vcards(text: str) -> list[Contact]:
    """Parse vCard text into a normalized contact dict list.

    Output shape per contact:
      {
        name: Optional[str]  # FN if present
        n: {
          family: str, given: str, additional: str, prefix: str, suffix: str
        } | None
        emails: List[{ value: str, types: List[str] }]
        phones: List[{ value: str, types: List[str] }]
        org: List[str] | None  # structured components
      }
    """
    contacts: list[Contact] = []
    for v in vobject.readComponents(text):
        # FN and structured N
        fn_obj = getattr(v, "fn", None)
        fn_val: str | None = fn_obj.value if fn_obj is not None else None

        n_struct: NameStruct | None = None
        n_obj = getattr(v, "n", None)
        if n_obj is not None:
            nval = n_obj.value  # vobject.vcard.Name
            n_struct = {
                "family": nval.family or "",
                "given": nval.given or "",
                "additional": nval.additional or "",
                "prefix": nval.prefix or "",
                "suffix": nval.suffix or "",
            }
        else:
            # Derive a minimal N from FN as best-effort using split helper
            n_struct = _split_name(str(fn_val)) if fn_val else None

        # Emails with types
        emails: list[EmailEntry] = []
        for e in getattr(v, "email_list", []):
            params = getattr(e, "params", {}) or {}
            singleton = getattr(e, "singletonparams", []) or []
            types = extract_types_from_params("email", params, singleton)
            emails.append({"value": e.value, "types": types})

        # Phones with types
        phones: list[PhoneEntry] = []
        for p in getattr(v, "tel_list", []):
            params = getattr(p, "params", {}) or {}
            singleton = getattr(p, "singletonparams", []) or []
            types = extract_types_from_params("tel", params, singleton)
            phones.append({"value": p.value, "types": types})

        # ORG structured components
        org_list = None
        org_obj = getattr(v, "org", None)
        if org_obj is not None:
            try:
                # Typically a list of components
                vals = org_obj.value or []
                org_list = [str(x) for x in vals]
            except Exception:
                # fallback: treat as a single string
                try:
                    org_list = [str(org_obj.value)]
                except Exception:
                    org_list = None

        # BDAY (date or datetime or text). Normalize to ISO if possible.
        bday_val = None
        bday_obj = getattr(v, "bday", None)
        if bday_obj is not None:
            try:
                val = bday_obj.value
                # vobject can yield date/datetime; convert to date string when possible
                if hasattr(val, "isoformat"):
                    # If datetime, take date part
                    try:
                        bday_val = val.date().isoformat()
                    except Exception:
                        bday_val = val.isoformat()
                else:
                    bday_val = str(val)
            except Exception:
                bday_val = None

        # NOTE can appear multiple times; collect as list of strings
        notes_list: list[str] | None = None
        note_props = getattr(v, "note_list", None)
        if note_props is not None:
            try:
                notes_list = [str(n.value) for n in (note_props or [])]
            except Exception:
                notes_list = None

        c: Contact = {
            "name": fn_val,
            "n": n_struct,
            "emails": emails,
            "phones": phones,
            "org": org_list,
            "bday": bday_val,
            "notes": notes_list,
        }
        contacts.append(c)
    return contacts


def contact_to_vcard40(c: Contact) -> str:
    props = [
        "BEGIN:VCARD",
        "VERSION:4.0",
    ]
    # FN
    name = c.get("name") or "Unnamed"
    # N (structured): family;given;additional;prefix;suffix
    n_struct = c.get("n") or {
        "family": "",
        "given": name,
        "additional": "",
        "prefix": "",
        "suffix": "",
    }
    n_fields = [
        escape_text(n_struct.get("family", "")),
        escape_text(n_struct.get("given", "")),
        escape_text(n_struct.get("additional", "")),
        escape_text(n_struct.get("prefix", "")),
        escape_text(n_struct.get("suffix", "")),
    ]
    props.append("N:" + ";".join(n_fields))
    props.append(f"FN:{escape_text(name)}")

    # EMAIL
    for e in c.get("emails", []):
        types = normalize_types("email", e.get("types", []))
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"EMAIL{type_param}:{escape_text(e.get('value',''))}")

    # TEL (VALUE=uri tel:...)
    for p in c.get("phones", []):
        tel = normalize_tel_uri(p.get("value", ""))
        types = normalize_types("tel", p.get("types", []))
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"TEL{type_param};VALUE=uri:{escape_text(tel)}")

    # ORG structured
    if c.get("org"):
        comps = [escape_text(str(comp)) for comp in (c.get("org") or [])]
        props.append("ORG:" + ";".join(comps))

    # BDAY (RFC 6350 date-and-or-time). Assume a simple date string like YYYY-MM-DD.
    if c.get("bday"):
        props.append(f"BDAY:{escape_text(str(c.get('bday')))}")

    # NOTE(s) – write each as separate NOTE property
    notes = c.get("notes") or []
    for note in notes:
        props.append(f"NOTE:{escape_text(str(note))}")

    # PRODID and UID
    props.append("PRODID:-//BetterVCardTools//v1.0//EN")
    # UID (RFC 6350 recommends a URI; use UUID URN)
    props.append(f"UID:urn:uuid:{uuid4()}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: list[Contact]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)
