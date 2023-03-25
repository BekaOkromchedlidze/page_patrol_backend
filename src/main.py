from fastapi import FastAPI

from .api import scraper

app = FastAPI()

app.include_router(scraper.router)
