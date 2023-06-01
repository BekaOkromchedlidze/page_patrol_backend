import os

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from src.api.patrol_history_mgmt import PatrolHistoryManagement
from src.api.patrol_mgmt import PatrolManagement
from src.api.scraper import Scraper
from src.auth_config import auth_config, azure_scheme
from src.table_storage import TableStorage
from src.util.http_headers_manager import HttpHeadersManager

app = FastAPI(
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": auth_config.OPENAPI_CLIENT_ID,
    },
)


@app.on_event("startup")
async def startup_event():
    setup_scheduler()


if auth_config.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in auth_config.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

table_storage = TableStorage()
patrol_management = PatrolManagement(table_storage)
patrol_history_management = PatrolHistoryManagement(table_storage)
headers_manager = HttpHeadersManager()
scraper = Scraper(table_storage, patrol_history_management, headers_manager)

app.include_router(scraper.router, dependencies=[Security(azure_scheme)])
app.include_router(patrol_management.router)
app.include_router(patrol_history_management.router)


def setup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scraper.process_page_patrol,
        trigger=IntervalTrigger(minutes=int(os.getenv("SCRAPER_INTERVAL", 1))),
        id="process_website_monitor",
        replace_existing=True,
    )
    scheduler.start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
