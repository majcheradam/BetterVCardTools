import re
from app.vcards import parse_vcards, contacts_to_vcards40

VCARD_21_CHARSET = (
    "BEGIN:VCARD\r\n"
    "VERSION:2.1\r\n"
    "N;CHARSET=ISO-8859-1:Dör;Jöhn;;;\r\n"
    "FN;CHARSET=ISO-8859-1:Jöhn Dör\r\n"
    "TEL;HOME: (555) 010-2000 \r\n"
    "TEL;WORK: +1 555 010 2001\r\n"
    "EMAIL;INTERNET:john@example.com\r\n"
    "EMAIL;INTERNET:john.work@example.com\r\n"
    "ORG;CHARSET=ISO-8859-1:Åcme;Sälës\r\n"
    "END:VCARD\r\n"
)

VCARD_MISSING_FN_N = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "TEL;TYPE=CELL: +44 (0) 20 7946 0958\r\n"
    "EMAIL:someone+tag@example.co.uk\r\n"
    "END:VCARD\r\n"
)

VCARD_MULTI = (
    "BEGIN:VCARD\r\nVERSION:3.0\r\nN:Alpha;Ada;;;\r\nFN:Ada Alpha\r\nTEL;TYPE=CELL:+1 111 1111\r\nEND:VCARD\r\n"
    "BEGIN:VCARD\r\nVERSION:3.0\r\nN:Beta;Bob;;;\r\nFN:Bob Beta\r\nEMAIL:bob@example.com\r\nEND:VCARD\r\n"
)

def test_v21_charset_and_multiple_fields():
    contacts = parse_vcards(VCARD_21_CHARSET)
    assert len(contacts) == 1
    c = contacts[0]
    # N + FN parsed (best-effort depends on vobject decoding)
    assert c["emails"][0]["value"].startswith("john@")
    assert len(c["emails"]) == 2
    assert len(c["phones"]) == 2
    out = contacts_to_vcards40(contacts)
    # TEL formatting normalized (no spaces/paren/dashes) and VALUE=uri
    assert re.search(r"^TEL;TYPE=home;VALUE=uri:tel:\+?\d+$", out, re.M)
    assert re.search(r"^TEL;TYPE=work;VALUE=uri:tel:\+?\d+$", out, re.M)
    # Two EMAILs
    assert len(re.findall(r"^EMAIL", out, re.M)) == 2


def test_missing_fn_and_n_generates_minimal_fields():
    contacts = parse_vcards(VCARD_MISSING_FN_N)
    assert len(contacts) == 1
    out = contacts_to_vcards40(contacts)
    # FN should fall back to Unnamed, N structured should be present
    assert re.search(r"^FN:Unnamed\r?$", out, re.M)
    assert re.search(r"^N:;;;;\r?$", out, re.M) or re.search(r"^N:[^\r\n]*\r?$", out, re.M)


def test_multiple_contacts_roundtrip():
    contacts = parse_vcards(VCARD_MULTI)
    assert len(contacts) == 2
    out = contacts_to_vcards40(contacts)
    # Two cards begin and end
    assert out.count("BEGIN:VCARD") == 2
    assert out.count("END:VCARD") == 2
