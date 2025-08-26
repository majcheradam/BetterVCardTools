import re

from app.vcards import contacts_to_vcards40, parse_vcards

SAMPLE = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "N:Doe;John;;;\r\n"
    "FN:John Doe\r\n"
    "TEL;TYPE=CELL,HOME: +1 555 0100\r\n"
    "EMAIL;TYPE=WORK:john.doe@example.com\r\n"
    "ORG:Acme;Sales\r\n"
    "END:VCARD\r\n"
)

def test_parse_and_serialize_types_and_org():
    contacts = parse_vcards(SAMPLE)
    assert len(contacts) == 1
    c = contacts[0]
    assert c["n"]["family"] == "Doe"
    assert c["n"]["given"] == "John"
    assert c["org"] == ["Acme", "Sales"]
    # Serialize
    out = contacts_to_vcards40(contacts)
    assert "VERSION:4.0" in out
    # TEL carries TYPEs and VALUE=uri (allow CRLF)
    assert re.search(r"^TEL;TYPE=cell,home;VALUE=uri:tel:\+15550100\r?$", out, re.M)
    # EMAIL TYPE=work (allow CRLF)
    assert re.search(r"^EMAIL;TYPE=work:john.doe@example.com\r?$", out, re.M)
    # UID present as UUID URN (allow CRLF)
    assert re.search(r"^UID:urn:uuid:[0-9a-fA-F-]{36}\r?$", out, re.M)
