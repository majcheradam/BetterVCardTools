# BetterVCardTools

Upload any vCard file (2.1/3.0/4.0) and download a normalized vCard 4.0.

What we keep today:
- Name (FN) and structured name (N)
- Email addresses with normalized TYPEs
- Phone numbers with normalized TYPEs and VALUE=uri tel:...
- Organization (ORG) components
- Birthday (BDAY) if present
- Notes (NOTE) — multiple notes are preserved

Other properties are currently omitted to keep the output lean; if you need more fields supported, please open an issue or PR.

## Local dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Docker
```bash
# build
docker build -t better-vcard-tools .
# run
docker run --rm -p 8000:8000 better-vcard-tools
```

## Deploy (Railway or similar)

- New Project → Deploy from Repo
- Add no special env vars (no auth needed)
- Done — ready to use

## Publish to GitHub (public)

1. Initialize git and commit:
```bash
git init
printf "venv\n.venv\n__pycache__\n*.pyc\n.env\n.DS_Store\n" > .gitignore
git add .
git commit -m "feat: BetterVCardTools MVP"
```
2. Create a public repo on GitHub (replace OWNER/REPO):
```bash
git remote add origin git@github.com:OWNER/BetterVCardTools.git
git branch -M main
git push -u origin main
```
