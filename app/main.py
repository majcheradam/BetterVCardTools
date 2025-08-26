import io
import os

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .vcards import contacts_to_vcards40, parse_vcards

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
# Ensure static directory exists to avoid needing a placeholder file in VCS
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile):
    data = await file.read()
    contacts = parse_vcards(data.decode(errors="ignore"))
    vcf_text = contacts_to_vcards40(contacts)
    # Derive download filename from uploaded file
    base = (file.filename or "contacts").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if base.lower().endswith('.vcf'):
        base = base[:-4]
    out_name = f"{base}-4.0.vcf"
    return StreamingResponse(
        io.BytesIO(vcf_text.encode("utf-8")),
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={out_name}"},
    )