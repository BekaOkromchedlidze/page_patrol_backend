from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from src.api import monitoring_mgmt, scraper

from .auth_config import auth_config, azure_scheme

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

app.include_router(scraper.router, dependencies=[Security(azure_scheme)])
app.include_router(monitoring_mgmt.router)


def setup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scraper.process_website_monitor,
        trigger=IntervalTrigger(minutes=1),
        id="process_website_monitor",
        replace_existing=True,
    )
    scheduler.start()
