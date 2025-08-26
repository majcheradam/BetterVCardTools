import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.vcards import parse_vcards, contacts_to_vcards40

SAMPLES = ROOT / 'tests' / 'smoke_vcards'

def run_one(name: str):
    text = (SAMPLES / name).read_text(encoding='utf-8')
    contacts = parse_vcards(text)
    out = contacts_to_vcards40(contacts)
    assert 'BEGIN:VCARD' in out and 'END:VCARD' in out, 'Missing vCard envelope'
    assert 'VERSION:4.0' in out, 'Output must be vCard 4.0'
    # All TEL must be VALUE=uri with tel:
    for line in out.splitlines():
        if line.startswith('TEL;'):
            assert ';VALUE=uri:' in line and 'tel:' in line, f'Bad TEL line: {line}'
    print(f"OK: {name} -> {len(contacts)} contact(s)")

if __name__ == '__main__':
    for fname in ['sample_21.vcf', 'sample_30.vcf', 'sample_40.vcf']:
        run_one(fname)
    print('Smoke tests passed.')
