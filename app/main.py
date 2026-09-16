from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import auth_router, checklist_router, clients_router, documents_router, drafts_router, risk_router

app = FastAPI(title="AI Estate Planning Agent")

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth_router.router)
app.include_router(clients_router.router)
app.include_router(documents_router.router)
app.include_router(drafts_router.router)
app.include_router(risk_router.router)
app.include_router(checklist_router.router)
