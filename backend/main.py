import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend import db
from backend.auth import get_api_key
from backend.routes import blocks

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> FastAPI:
    application = FastAPI(title="rozvrh")
    application.include_router(blocks.router)
    db.init_db()
    get_api_key()
    if os.path.isdir(STATIC_DIR):
        application.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return application


app = create_app()
