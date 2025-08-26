# BetterVCardTools

Convert any vCard (2.1/3.0/4.0) to a clean, strict vCard 4.0 in UTF‑8.

See also: roadmap with phases and actionable checklist → [roadmap.md](./roadmap.md)

## Features

- Input: vCard 2.1/3.0/4.0 → Output: vCard 4.0 (UTF‑8)
- Strict serializer: CRLF endings, 75‑octet folding, proper escaping, caret‑encoded params
- Names: FN + structured N (derived from FN when missing)
- Emails: multiple entries, normalized TYPEs, PREF=1 when preferred
- Phones: VALUE=uri tel:…, normalized TYPEs, PREF=1 when preferred
- Addresses: ADR (structured) with TYPE/PREF and optional LABEL
- ORG components
- BDAY if present
- Multiple NOTE lines
- URL and IMPP as URIs
- GEO “lat;long” → geo:lat,long; TZ as text/offset
- Media/keys: PHOTO/LOGO/SOUND/KEY as VALUE=uri
- Metadata: PRODID, UID (preserved if present; otherwise urn:uuid:…), REV (UTC)

## Roadmap by phases

### Phase 1 – Core Foundation
Goal: Get a working converter, support all vCard versions

- Upload .vcf (supports vCard 2.1 / 3.0 / 4.0)
- Detect encoding, convert to UTF‑8
- Normalize line endings & folding
- Expand/fix QUOTED‑PRINTABLE + BASE64
- Map old fields → vCard 4.0 (e.g., TEL;HOME;VOICE → TEL;TYPE=home,voice)
- Drop unsupported fields (LABEL, AGENT, MAILER, etc.)
- Ensure FN (Formatted Name) present
- Generate UID if missing
- Export: strict vCard 4.0 UTF‑8 (multi‑contact supported)

### Phase 2 – Validation & Cleaning
Goal: Trustworthy output, clear feedback

- Unicode normalization (NFC)
- Fix common mojibake (Polish ł/ń, German ß, French é/è, etc.)
- Strip invisible chars (BOM, zero‑width space)
- Enforce RFC 6350 strictness
- Report: show warnings (fields dropped, fixed, normalized)
- Contact preview (before download)

### Phase 3 – Deduplication & Smart Normalization
Goal: Better quality contacts, not just conversion

- Duplicate detection (EMAIL, TEL, FN)
- Merge strategy options (keep longest, newest, manual)
- Normalize phone numbers → E.164 format (with default region)
- Clean URLs (https, lowercase)
- Normalize addresses (consistent structure: STREET, CITY, ZIP, COUNTRY)
- Normalize property casing (TEL not tel)

### Phase 4 – Import/Export Flexibility
Goal: Play nice with ecosystems & power users

- Import .vcf & .csv
- Export .vcf & .csv
- Option: one .vcf per contact
- Batch processing (thousands of contacts)
- CLI tool (for power users)
- REST API endpoint for developers

### Phase 5 – UX & Privacy Enhancements
Goal: Smooth user experience, privacy guaranteed

- Drag‑and‑drop upload
- Offline‑first mode (PWA, all in‑browser)
- Error logs & downloadable validation report
- Multi‑language UI (English, Polish, German, French, etc.)
- Dark mode & modern responsive UI
- Privacy modes:
	- Local‑only (browser‑side conversion)
	- Serverless (Railway, Vercel)

## Quick start

Local dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000

Docker
```bash
docker build -t better-vcard-tools .
docker run --rm -p 8000:8000 better-vcard-tools
```

Deploy: use any container host (no env vars needed).

Contribute: issues and PRs welcome.
