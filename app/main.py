from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import io

from .vcards import parse_vcards, contacts_to_vcards40

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
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
    return StreamingResponse(
        io.BytesIO(vcf_text.encode("utf-8")),
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=contacts-4.0.vcf"},
    )