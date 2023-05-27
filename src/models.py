import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    name: str
    email: str
    oid: str


ScrapeInterval = [1, 5, 15, 30, 60, 240, 720, 1440]


class PagePatrol(BaseModel):
    PartitionKey: str
    RowKey: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date_added: int
    url: str
    xpath: str
    search_string: str
    scrape_interval: int
    is_enabled: bool = True
    is_deleted: bool = False
    last_scrape_time: Optional[datetime] = None
    last_scrape_status: Optional[str] = None
    last_scrape_status_detail: Optional[str] = None
    last_scrape_html_content: Optional[str] = None


class PatrolHistory(BaseModel):
    PartitionKey: str
    RowKey: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_patrol_id: str
    scrape_time: datetime
    scrape_status: str
    scrape_status_detail: str
    scrape_html_content: str
