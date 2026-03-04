from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/", response_class=HTMLResponse)
def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
