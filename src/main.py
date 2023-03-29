from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from src.auth_config import auth_config, azure_scheme

from .api import monitoring_mgmt, scraper

app = FastAPI(
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": auth_config.OPENAPI_CLIENT_ID,
    },
)

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
