from typing import Union

from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from pydantic import AnyHttpUrl, BaseSettings, Field


class AuthConfig(BaseSettings):
    SECRET_KEY: str = Field(default="", env="SECRET_KEY")
    BACKEND_CORS_ORIGINS: list[Union[str, AnyHttpUrl]] = ["http://localhost:8000"]
    OPENAPI_CLIENT_ID: str = Field(default="", env="OPENAPI_CLIENT_ID")
    APP_CLIENT_ID: str = Field(default="", env="APP_CLIENT_ID")
    TENANT_ID: str = Field(default="", env="TENANT_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


auth_config = AuthConfig()
azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=auth_config.APP_CLIENT_ID,
    tenant_id=auth_config.TENANT_ID,
    scopes={
        f"api://{auth_config.APP_CLIENT_ID}/user_impersonation": "user_impersonation",
    },
)
