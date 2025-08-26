import vobject, re
from typing import List, Dict

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
    contacts = []
    for v in vobject.readComponents(text):
        c = {
            "name": getattr(v, 'fn', None).value if hasattr(v, 'fn') else None,
            "emails": [e.value for e in getattr(v, 'email_list', [])],
            "phones": [p.value for p in getattr(v, 'tel_list', [])],
            "org": v.org.value[0] if hasattr(v, 'org') else None,
        }
        contacts.append(c)
    return contacts


def contact_to_vcard40(c: Dict) -> str:
    props = [
        "BEGIN:VCARD",
        "VERSION:4.0",
    ]
    name = c.get("name") or "Unnamed"
    props.append(f"N:;{_escape(name)};;;")
    props.append(f"FN:{_escape(name)}")
    for e in c.get("emails", []):
        props.append(f"EMAIL:{_escape(e)}")
    for p in c.get("phones", []):
        tel = re.sub(r"\s+", "", str(p))
        if not tel.startswith("tel:"):
            tel = f"tel:{tel}"
        props.append(f"TEL;TYPE=cell;VALUE=uri:{_escape(tel)}")
    if c.get("org"):
        props.append(f"ORG:{_escape(c['org'])}")
    props.append("END:VCARD")
    return CRLF.join(props) + CRLF


def contacts_to_vcards40(contacts: List[Dict]) -> str:
    return "".join(contact_to_vcard40(c) for c in contacts)
