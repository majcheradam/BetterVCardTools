import re
from typing import Optional
from uuid import uuid4

import vobject

CRLF = "\r\n"


def _escape(s: str) -> str:
    if not s:
        return ""
    return (str(s)
            .replace("\\", "\\\\")
            .replace(";", r"\\;")
            .replace(",", r"\\,")
            .replace("\n", r"\\n")
            .replace("\r", ""))

_PREFIXES = {"mr", "mrs", "ms", "dr", "prof"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}

def _split_name(fn: str) -> dict[str, str]:
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
    # Dedup, lowercase done in _split_types; filter unwanted values
    tset = set(types or [])
    if kind == "email":
        # RFC 6350 removed INTERNET; it's implied, so drop it
        tset.discard("internet")
    if kind == "tel" and len(tset) > 1 and "voice" in tset:
        # Drop 'voice' if there are other types present
        tset.remove("voice")
    return sorted(tset)

_KNOWN_TEL_TYPES = {
    "home", "work", "cell", "voice", "fax", "pager", "text", "textphone", "main", "iphone"
}
_KNOWN_EMAIL_TYPES = {"home", "work", "internet", "pref", "x-mobileme"}

def _extract_types_from_params(kind: str, params: dict, singletonparams) -> list[str]:
    types: list[str] = []
    p = params or {}
    # TYPE values (comma-joined or list)
    if 'TYPE' in p:
        types.extend(_split_types(p.get('TYPE')))
    # vCard 2.1 style: bare flags like HOME/WORK appear as parameter keys
    for key, _val in p.items():
        k = str(key).lower()
        if k == 'type':
            continue
        if kind == 'tel' and k in _KNOWN_TEL_TYPES:
            types.append(k)
        if kind == 'email' and k in _KNOWN_EMAIL_TYPES:
            types.append(k)
    # singletonparams fallback (some vobject versions)
    if singletonparams:
        types.extend(_split_types(singletonparams))
    return _normalize_types(kind, types)

essential_fields = ("fn", "email_list", "tel_list", "org")

def parse_vcards(text: str) -> list[dict]:
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
    contacts: list[dict] = []
    for v in vobject.readComponents(text):
        # FN and structured N
        fn_obj = getattr(v, 'fn', None)
        fn_val: Optional[str] = fn_obj.value if fn_obj is not None else None
        n_struct = None
        n_obj = getattr(v, 'n', None)
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
        emails = []
        for e in getattr(v, 'email_list', []):
            params = getattr(e, 'params', {}) or {}
            singleton = getattr(e, 'singletonparams', []) or []
            types = _extract_types_from_params('email', params, singleton)
            emails.append({"value": e.value, "types": types})

        # Phones with types
        phones = []
        for p in getattr(v, 'tel_list', []):
            params = getattr(p, 'params', {}) or {}
            singleton = getattr(p, 'singletonparams', []) or []
            types = _extract_types_from_params('tel', params, singleton)
            phones.append({"value": p.value, "types": types})

        # ORG structured components
        org_list = None
        org_obj = getattr(v, 'org', None)
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
        bday_obj = getattr(v, 'bday', None)
        if bday_obj is not None:
            try:
                val = bday_obj.value
                # vobject can yield date/datetime; convert to date string when possible
                if hasattr(val, 'isoformat'):
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
        note_props = getattr(v, 'note_list', None)
        if note_props is not None:
            try:
                notes_list = [str(n.value) for n in (note_props or [])]
            except Exception:
                notes_list = None

        c = {
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


def contact_to_vcard40(c: dict) -> str:
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
        _escape(n_struct.get("family", "")),
        _escape(n_struct.get("given", "")),
        _escape(n_struct.get("additional", "")),
        _escape(n_struct.get("prefix", "")),
        _escape(n_struct.get("suffix", "")),
    ]
    props.append("N:" + ";".join(n_fields))
    props.append(f"FN:{_escape(name)}")

    # EMAIL
    for e in c.get("emails", []):
        types = _normalize_types("email", e.get("types", []))
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"EMAIL{type_param}:{_escape(e.get('value',''))}")

    # TEL (VALUE=uri tel:...)
    for p in c.get("phones", []):
        tel_raw = str(p.get("value", ""))
        # Remove whitespace and common punctuation, keep leading '+' if present
        tel = re.sub(r"[\s()\-.]", "", tel_raw)
        if not tel.startswith("tel:"):
            tel = f"tel:{tel}"
        types = _normalize_types("tel", p.get("types", []))
        type_param = f";TYPE={','.join(types)}" if types else ""
        props.append(f"TEL{type_param};VALUE=uri:{_escape(tel)}")

    # ORG structured
    if c.get("org"):
        comps = [
            _escape(str(comp)) for comp in (c.get("org") or [])
        ]
        props.append("ORG:" + ";".join(comps))

    # BDAY (RFC 6350 date-and-or-time). Assume a simple date string like YYYY-MM-DD.
    if c.get("bday"):
        props.append(f"BDAY:{_escape(str(c.get('bday')))}")

    # NOTE(s) – write each as separate NOTE property
    notes = c.get("notes") or []
    for note in notes:
        props.append(f"NOTE:{_escape(str(note))}")

    # PRODID and UID
    props.append("PRODID:-//BetterVCardTools//v1.0//EN")
    # UID (RFC 6350 recommends a URI; use UUID URN)
    props.append(f"UID:urn:uuid:{uuid4()}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: list[dict]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)
