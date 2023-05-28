from datetime import datetime
from operator import itemgetter
from typing import Optional, Union

from azure.data.tables import UpdateMode
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_azure_auth.user import User

from src.auth_config import azure_scheme
from src.models import PagePatrol, ScrapeInterval, UserInfo
from src.table_storage import TableStorage


class PatrolManagement:
    def __init__(self, table_storage: TableStorage):
        self.table_storage = table_storage
        self.router = APIRouter()

        self.router.post("/page-patrol", response_model=PagePatrol)(
            self.add_page_patrol_entity
        )
        self.router.get("/page-patrol")(self.get_patrol_entities)
        self.router.put("/page-patrol/{page_patrol_id}")(self.update_patrol_entity)
        self.router.delete(
            "/page-patrol/{page_patrol_id}", response_model=dict[str, bool]
        )(self.delete_patrol_entity)
        self.router.put(
            "/page-patrol/{page_patrol_id}/toggle",
            response_model=dict[str, Union[bool, str]],
        )(self.toggle_patrol_entity)

    # Add a new patrol entity
    async def add_page_patrol_entity(
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
    async def get_patrol_entities(self, user: User = Depends(azure_scheme)):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Query the table storage for entries belonging to the authenticated user
        entities = self.table_storage.query_entities(
            self.table_storage.page_patrol_table_client,
            query_filter=f"PartitionKey eq '{user_info.oid}' and is_deleted eq false",
        )
        # Sort entries based on Timestamp in descending order
        entities = sorted(entities, key=itemgetter("date_added"), reverse=True)

        return [dict(entity.items()) for entity in entities]

    # Update an existing patrol entity
    async def update_patrol_entity(
        self,
        page_patrol_id: str = Path(...),
        url: Optional[str] = None,
        xpath: Optional[str] = None,
        search_string: Optional[str] = None,
        scrape_interval: Optional[int] = Query(None, enum=ScrapeInterval),
        user: User = Depends(azure_scheme),
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Get the patrol entity from the table storage
        entity = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, page_patrol_id
        )
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        if url:
            entity["url"] = url
        if xpath:
            entity["xpath"] = xpath
        if search_string:
            entity["search_string"] = search_string
        if scrape_interval:
            entity["scrape_interval"] = scrape_interval

        # Update the entity with the new data
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entity,
        )

        return {"success": True}

    # Soft delete a patrol entity
    async def delete_patrol_entity(
        self, patrol_entity_id: str = Path(...), user: User = Depends(azure_scheme)
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)

        # Get the patrol entity from the table storage
        entity = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, patrol_entity_id
        )
        if not entity:
            raise HTTPException(status_code=404, detail="entity not found")

        # Set the is_deleted flag to True for soft deletion
        entity["is_deleted"] = True
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entity,
        )

        return {"success": True}

    # Enable or disable a patrol entity
    async def toggle_patrol_entity(
        self, patrol_entity_id: str = Path(...), user: User = Depends(azure_scheme)
    ):
        # Get user information from the authentication system
        user_info = await self.get_user_info(user)
        # Get the patrol entity from the table storage
        entity = self.table_storage.get_entity(
            self.table_storage.page_patrol_table_client, user_info.oid, patrol_entity_id
        )
        if not entity:
            raise HTTPException(status_code=404, detail="entity not found")

        # Toggle the is_enabled flag
        self.update_entity_helper(entity, is_enabled=not entity["is_enabled"])

        return {"success": True, "is_enabled": entity["is_enabled"]}

    async def get_user_info(self, user: User) -> UserInfo:
        # Extract relevant user information from the User object
        name = user.dict()["name"]
        preferred_username = user.dict()["claims"]["preferred_username"]
        oid = user.dict()["claims"]["oid"]

        # Create a UserInfo object with the extracted information
        user_info = UserInfo(name=name, email=preferred_username, oid=oid)

        return user_info

    def update_entity_helper(
        self, entity, url=None, xpath=None, search_string=None, is_enabled=None
    ):
        # Update the entity fields if new values are provided
        if url:
            entity["url"] = url
        if xpath:
            entity["xpath"] = xpath
        if search_string:
            entity["search_string"] = search_string
        if is_enabled is not None:
            entity["is_enabled"] = is_enabled

        # Update the entity in the table storage
        self.table_storage.update_entity(
            self.table_storage.page_patrol_table_client,
            mode=UpdateMode.REPLACE,
            entity=entity,
        )
