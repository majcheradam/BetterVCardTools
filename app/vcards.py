import vobject, re
from typing import List, Dict, Optional, TypedDict
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
            # Derive a minimal N from FN as best-effort
            if fn_val:
                parts = str(fn_val).strip().split()
                if len(parts) >= 2:
                    n_struct = {"family": " ".join(parts[1:]), "given": parts[0], "additional": "", "prefix": "", "suffix": ""}
                else:
                    n_struct = {"family": "", "given": parts[0] if parts else "", "additional": "", "prefix": "", "suffix": ""}

        # Emails with types
        emails = []
        for e in getattr(v, 'email_list', []):
            types = e.params.get('TYPE', []) if hasattr(e, 'params') else []
            # vobject may provide a single string or list
            if isinstance(types, str):
                types = [types]
            emails.append({"value": e.value, "types": [str(t).lower() for t in types]})

        # Phones with types
        phones = []
        for p in getattr(v, 'tel_list', []):
            types = p.params.get('TYPE', []) if hasattr(p, 'params') else []
            if isinstance(types, str):
                types = [types]
            phones.append({"value": p.value, "types": [str(t).lower() for t in types]})

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
        types = e.get("types", [])
        type_param = f";TYPE={','.join(sorted(set(t for t in types if t)))}" if types else ""
        props.append(f"EMAIL{type_param}:{_escape(e.get('value',''))}")

    # TEL (VALUE=uri tel:...)
    for p in c.get("phones", []):
        tel_raw = str(p.get("value", ""))
        tel = re.sub(r"\s+", "", tel_raw)
        if not tel.startswith("tel:"):
            tel = f"tel:{tel}"
        types = p.get("types", [])
        type_param = f";TYPE={','.join(sorted(set(t for t in types if t)))}" if types else ""
        props.append(f"TEL{type_param};VALUE=uri:{_escape(tel)}")

    # ORG structured
    if c.get("org"):
        comps = [
            _escape(str(comp)) for comp in (c.get("org") or [])
        ]
        props.append("ORG:" + ";".join(comps))

    # UID
    props.append(f"UID:{uuid4()}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: List[Dict]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)
