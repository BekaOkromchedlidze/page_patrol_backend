from datetime import datetime
from operator import itemgetter
from typing import Optional, Union

from azure.data.tables import UpdateMode
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_azure_auth.user import User

from ..auth_config import azure_scheme
from ..models import PagePatrol, ScrapeInterval, UserInfo
from ..table_storage import TableStorage


class PatrolManagement:
    def __init__(self, table_storage: TableStorage):
        self.table_storage = table_storage
        self.router = APIRouter()

        self.router.post("/page-patrol", response_model=PagePatrol)(self.add_entry)
        self.router.get("/page-patrol")(self.get_entries)
        self.router.put("/page-patrol/{entry_id}")(self.update_entry)
        self.router.delete("/page-patrol/{entry_id}", response_model=dict[str, bool])(
            self.delete_entry
        )
        self.router.put(
            "/page-patrol/{entry_id}/toggle",
            response_model=dict[str, Union[bool, str]],
        )(self.toggle_entry)

    # Add a new patrol entry
    async def add_entry(
        self,
        url: str,
        xpath: str,
        search_string: str,
        scrape_interval: int = Query(1, enum=ScrapeInterval),
        user: User = Depends(azure_scheme),
    ) -> dict[str, bool]:
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)

        # Create a new PagePatrol object with the given data
        page_patrol = PagePatrol(
            PartitionKey=user_info.oid,
            date_added=int(datetime.now().timestamp()),
            url=url,
            xpath=xpath,
            search_string=search_string,
            scrape_interval=scrape_interval,
            is_enabled=True,
            is_deleted=False,
        )
        try:
            # Add the new PagePatrol object to the table storage
            self.table_storage.create_entity(
                self.table_storage.page_patrol_table_client,
                entity=page_patrol.dict(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        return page_patrol.dict()

    # Retrieve all patrol entries for the authenticated user
    async def get_entries(self, user: User = Depends(azure_scheme)):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Query the table storage for entries belonging to the authenticated user
        entries = self.table_storage.query_entities(
            self.table_storage.page_patrol_table_client,
            query_filter=f"PartitionKey eq '{user_info.oid}' and is_deleted eq false",
        )
        # Sort entries based on Timestamp in descending order
        entries = sorted(entries, key=itemgetter("date_added"), reverse=True)

        return [dict(entry.items()) for entry in entries]

    # Update an existing patrol entry
    async def update_entry(
        self,
        entry_id: str = Path(...),
        url: Optional[str] = None,
        xpath: Optional[str] = None,
        search_string: Optional[str] = None,
        scrape_interval: Optional[int] = Query(None, enum=ScrapeInterval),
        user: User = Depends(azure_scheme),
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Get the patrol entry from the table storage
        entry = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, entry_id
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        if url:
            entry["url"] = url
        if xpath:
            entry["xpath"] = xpath
        if search_string:
            entry["search_string"] = search_string
        if scrape_interval:
            entry["scrape_interval"] = scrape_interval

        # Update the entry with the new data
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entry,
        )

        return {"success": True}

    # Soft delete a patrol entry
    async def delete_entry(
        self, entry_id: str = Path(...), user: User = Depends(azure_scheme)
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)

        # Get the patrol entry from the table storage
        entry = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, entry_id
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Set the is_deleted flag to True for soft deletion
        entry["is_deleted"] = True
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entry,
        )

        return {"success": True}

    # Enable or disable a patrol entry
    async def toggle_entry(
        self, entry_id: str = Path(...), user: User = Depends(azure_scheme)
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Get the patrol entry from the table storage
        entry = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, entry_id
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Toggle the is_enabled flag
        self.update_entry_helper(entry, is_enabled=not entry["is_enabled"])

        return {"success": True, "is_enabled": entry["is_enabled"]}

    async def get_user_info(self, user: User) -> UserInfo:
        # Extract relevant user information from the User object
        name = user.dict()["name"]
        preferred_username = user.dict()["claims"]["preferred_username"]
        oid = user.dict()["claims"]["oid"]

        # Create a UserInfo object with the extracted information
        user_info = UserInfo(name=name, email=preferred_username, oid=oid)

        return user_info

    def update_entry_helper(
        self, entry, url=None, xpath=None, search_string=None, is_enabled=None
    ):
        # Update the entry fields if new values are provided
        if url:
            entry["url"] = url
        if xpath:
            entry["xpath"] = xpath
        if search_string:
            entry["search_string"] = search_string
        if is_enabled is not None:
            entry["is_enabled"] = is_enabled

        # Update the entry in the table storage
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entry,
        )
