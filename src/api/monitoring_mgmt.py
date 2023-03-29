from typing import Optional, Union

from azure.data.tables import UpdateMode
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi_azure_auth.user import User

from ..auth_config import azure_scheme
from ..models import UserInfo, WebsiteMonitor
from ..table_storage import website_monitoring_table_client

router = APIRouter()


# POST: Add a new monitoring entry
@router.post("/website-monitor", response_model=WebsiteMonitor)
async def add_entry(
    url: str,
    xpath: str,
    search_string: str,
    user: User = Depends(azure_scheme),
) -> dict[str, bool]:
    # Get user information from the authentication system
    user_info = await get_user_info(user)

    # Create a new WebsiteMonitor object with the given data
    website_monitor = WebsiteMonitor(
        PartitionKey=user_info.oid,
        url=url,
        xpath=xpath,
        search_string=search_string,
        is_enabled=True,
        is_deleted=False,
    )
    try:
        # Add the new WebsiteMonitor object to the table storage
        website_monitoring_table_client.create_entity(entity=website_monitor.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return website_monitor.dict()


# GET: Retrieve all monitoring entries for the authenticated user
@router.get("/website-monitor")
async def get_entries(user: User = Depends(azure_scheme)):
    # Get user information from the authentication system
    user_info = await get_user_info(user)
    # Query the table storage for entries belonging to the authenticated user
    entries = website_monitoring_table_client.query_entities(
        query_filter=f"PartitionKey eq '{user_info.oid}' and is_deleted eq false"
    )
    # Return the entries as a list of dictionaries
    return [dict(entry.items()) for entry in entries]


# PUT: Update an existing monitoring entry
@router.put("/website-monitor/{entry_id}")
async def update_entry(
    entry_id: str = Path(...),
    url: Optional[str] = None,
    xpath: Optional[str] = None,
    search_string: Optional[str] = None,
    user: User = Depends(azure_scheme),
):
    # Get user information from the authentication system
    user_info = await get_user_info(user)
    # Get the monitoring entry from the table storage
    entry = website_monitoring_table_client.get_entity(user_info.oid, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if url:
        entry["url"] = url
    if xpath:
        entry["xpath"] = xpath
    if search_string:
        entry["search_string"] = search_string

    # Update the entry with the new data
    website_monitoring_table_client.update_entity(mode=UpdateMode.REPLACE, entity=entry)

    return {"success": True}


# DELETE: Soft delete a monitoring entry
@router.delete("/entry/{entry_id}", response_model=dict[str, bool])
async def delete_entry(entry_id: str = Path(...), user: User = Depends(azure_scheme)):
    # Get user information from the authentication system
    user_info = await get_user_info(user)

    # Get the monitoring entry from the table storage
    entry = website_monitoring_table_client.get_entity(user_info.oid, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Set the is_deleted flag to True for soft deletion
    entry["is_deleted"] = True
    website_monitoring_table_client.update_entity(mode=UpdateMode.REPLACE, entity=entry)

    return {"success": True}


# PUT: Enable or disable a monitoring entry
@router.put("/entry/{entry_id}/toggle", response_model=dict[str, Union[bool, str]])
async def toggle_entry(entry_id: str = Path(...), user: User = Depends(azure_scheme)):
    # Get user information from the authentication system
    user_info = await get_user_info(user)
    # Get the monitoring entry from the table storage
    entry = website_monitoring_table_client.get_entity(user_info.oid, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Toggle the is_enabled flag
    update_entry_helper(entry, is_enabled=not entry["is_enabled"])

    return {"success": True, "is_enabled": entry["is_enabled"]}


async def get_user_info(user: User) -> UserInfo:
    # Extract relevant user information from the User object
    name = user.dict()["name"]
    preferred_username = user.dict()["claims"]["preferred_username"]
    oid = user.dict()["claims"]["oid"]

    # Create a UserInfo object with the extracted information
    user_info = UserInfo(name=name, email=preferred_username, oid=oid)

    return user_info


def update_entry_helper(
    entry, url=None, xpath=None, search_string=None, is_enabled=None
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
    website_monitoring_table_client.update_entity(mode=UpdateMode.REPLACE, entity=entry)
