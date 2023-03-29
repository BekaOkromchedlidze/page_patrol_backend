import uuid

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    name: str
    email: str
    oid: str


class WebsiteMonitor(BaseModel):
    PartitionKey: str
    RowKey: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    xpath: str
    search_string: str
    is_enabled: bool = True
    is_deleted: bool = False
