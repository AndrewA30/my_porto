from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .routers import portofolio, auth, admin
from .database import engine
from . import models

# create all database tables, jika menggunakan alembic, maka baris ini bisa di comment atau dihapus
models.Base.metadata.create_all(bind=engine)


app = FastAPI()

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

origins = [
    "https://www.google.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Include routers
app.include_router(portofolio.router)
app.include_router(auth.router)
app.include_router(admin.router)