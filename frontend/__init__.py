from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

# Membuat "mini-aplikasi" khusus frontend
run = APIRouter()

direktori_skrip = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=f"{direktori_skrip}")


@run.get("/")
async def home_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="/index.html"
    )
