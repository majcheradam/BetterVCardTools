from app.vcards import parse_vcards, contacts_to_vcards40
import re

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

def test_peek_v21_charset_basic_roundtrip():
    contacts = parse_vcards(VCARD_21_CHARSET)
    assert len(contacts) == 1
    out = contacts_to_vcards40(contacts)
    # Basic invariants
    assert 'BEGIN:VCARD' in out and 'END:VCARD' in out and 'VERSION:4.0' in out
    # UID urn uuid
    assert re.search(r"^UID:urn:uuid:[0-9a-fA-F-]{36}\r?$", out, re.M)
