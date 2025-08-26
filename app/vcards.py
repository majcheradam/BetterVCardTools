import vobject, re
from typing import List, Dict, Optional
from uuid import uuid4

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

def _split_name(fn: str) -> Dict[str, str]:
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
    core = tokens[1:-1] if (prefix and suffix) else (tokens[1:] if prefix else (tokens[:-1] if suffix else tokens))
    if not core:
        return {"family": "", "given": tokens[0] if tokens else "", "additional": "", "prefix": prefix, "suffix": suffix}
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

def _split_types(val) -> List[str]:
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

def _normalize_types(kind: str, types: List[str]) -> List[str]:
    # Dedup, lowercase done in _split_types; filter unwanted values
    tset = set(types or [])
    if kind == "email":
        # RFC 6350 removed INTERNET; it's implied, so drop it
        tset.discard("internet")
    if kind == "tel":
        # Drop 'voice' if there are other types present
        if len(tset) > 1 and "voice" in tset:
            tset.remove("voice")
    return sorted(tset)

_KNOWN_TEL_TYPES = {
    "home", "work", "cell", "voice", "fax", "pager", "text", "textphone", "main", "iphone"
}
_KNOWN_EMAIL_TYPES = {"home", "work", "internet", "pref", "x-mobileme"}

def _extract_types_from_params(kind: str, params: Dict, singletonparams) -> List[str]:
    types: List[str] = []
    p = params or {}
    # TYPE values (comma-joined or list)
    if 'TYPE' in p:
        types.extend(_split_types(p.get('TYPE')))
    # vCard 2.1 style: bare flags like HOME/WORK appear as parameter keys
    for key, val in p.items():
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

def parse_vcards(text: str) -> List[Dict]:
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
    contacts: List[Dict] = []
    for v in vobject.readComponents(text):
        # FN and structured N
        fn_val: Optional[str] = getattr(v, 'fn', None).value if hasattr(v, 'fn') else None
        n_struct = None
        if hasattr(v, 'n') and getattr(v, 'n', None) is not None:
            nval = v.n.value  # vobject.vcard.Name
            n_struct = {
                "family": nval.family or "",
                "given": nval.given or "",
                "additional": nval.additional or "",
                "prefix": nval.prefix or "",
                "suffix": nval.suffix or "",
            }
        else:
            # Derive a minimal N from FN as best-effort using split helper
            if fn_val:
                n_struct = _split_name(str(fn_val))
            else:
                n_struct = None

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
        if hasattr(v, 'org') and v.org is not None:
            try:
                # Typically a list of components
                vals = v.org.value or []
                org_list = [str(x) for x in vals]
            except Exception:
                # fallback: treat as a single string
                org_list = [str(v.org.value)]

        c = {
            "name": fn_val,
            "n": n_struct,
            "emails": emails,
            "phones": phones,
            "org": org_list,
        }
        contacts.append(c)
    return contacts


def contact_to_vcard40(c: Dict) -> str:
    props = [
        "BEGIN:VCARD",
        "VERSION:4.0",
    ]
    # FN
    name = c.get("name") or "Unnamed"
    # N (structured): family;given;additional;prefix;suffix
    n_struct = c.get("n") or {"family": "", "given": name, "additional": "", "prefix": "", "suffix": ""}
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

    # PRODID and UID
    props.append("PRODID:-//BetterVCardTools//v1.0//EN")
    # UID (RFC 6350 recommends a URI; use UUID URN)
    props.append(f"UID:urn:uuid:{uuid4()}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: List[Dict]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)
