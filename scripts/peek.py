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

contacts = parse_vcards(VCARD_21_CHARSET)
print('Parsed:', contacts)
vcf = contacts_to_vcards40(contacts)
print('Output:\n' + vcf)
