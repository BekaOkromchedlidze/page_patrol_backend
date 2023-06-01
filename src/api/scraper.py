from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
from azure.data.tables import UpdateMode
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from requests_html import AsyncHTMLSession

from src.api.patrol_history_mgmt import PatrolHistoryManagement
from src.logger_config import setup_logger
from src.table_storage import TableStorage
from src.util.http_headers_manager import HttpHeadersManager


class Scraper:
    def __init__(
        self,
        table_storage: TableStorage,
        patrol_history_mgmt: PatrolHistoryManagement,
        headers_manager: HttpHeadersManager,
    ):
        self.router = APIRouter()
        self.logger = setup_logger(__name__)
        self.table_storage = table_storage
        self.patrol_history_mgmt = patrol_history_mgmt
        self.headers_manager = headers_manager

    # Given url, element_xpath and search_string, search for search_string within the element and return its HTML if found.
    async def is_string_within_element(self, url, xpath, search_string):
        asession = AsyncHTMLSession()
        headers = await self.headers_manager.get_headers(url)
        resp = await asession.get(url, headers=headers)  # type: ignore

        # Get base_url
        base_url = self.get_baseurl_from(url)

        # Select the elements
        elements = resp.html.xpath(xpath)

        if not elements:
            return (
                "web_element_not_found",
                (
                    f"Could not find any web element from xpath: {xpath}"
                    f" Please double check the xpath."
                ),
                "",
            )

        # Multiple web elements found
        if len(elements) > 1:
            return (
                "multiple_elements_found",
                (
                    f"More than one web element found from xpath: {xpath}"
                    f" Please provide an xpath for a unique web element."
                ),
                "",
            )

        # One element found
        element = elements[0]
        # Check if string exists within the web element or any of its child elements
        if search_string in element.text or any(
            search_string in child.text for child in element.xpath(".//*")
        ):
            return (
                "found",
                "Found string within the web element.",
                element.html.replace('href="/', f'href="{base_url}/'),
            )
        else:
            return (
                "string_not_found",
                "Did not find the string within the web element.",
                "",
            )

    def get_response(self, status_code, status_detail, html_content):
        return JSONResponse(
            status_code=status_code,
            content={
                "code": status_code,
                "message": status_detail,
                "data": {"html": html_content},
            },
        )

    async def get_element_html(self, url: str, element_xpath: str, search_string: str):
        self.logger.info(f"Searching for: {search_string} on {url}")
        (
            req_status,
            req_status_detail,
            req_html_content,
        ) = await self.is_string_within_element(url, element_xpath, search_string)

        status_map = {
            "found": status.HTTP_200_OK,
            "web_element_not_found": status.HTTP_400_BAD_REQUEST,
            "multiple_elements_found": status.HTTP_400_BAD_REQUEST,
            "string_not_found": status.HTTP_404_NOT_FOUND,
        }

        return self.get_response(
            status_map.get(req_status, status.HTTP_500_INTERNAL_SERVER_ERROR),
            req_status_detail,
            req_html_content,
        )

    async def process_page_patrol(self):
        self.logger.info("Starting process_page_patrol")

        utc = pytz.UTC
        now = datetime.utcnow().replace(tzinfo=utc)

        # Get all enabled and not deleted page_patrol entries
        entities = self.table_storage.query_entities(
            self.table_storage.page_patrol_table_client,
            query_filter="is_enabled eq true and is_deleted eq false",
        )
        for entity in entities:
            # Calculate the elapsed time since the last scrape attempt
            last_scrape_time = entity.get("last_scrape_time", None)
            if last_scrape_time:
                time_elapsed = now - last_scrape_time
            else:
                time_elapsed = timedelta(minutes=entity["scrape_interval"])

            # Check if the time elapsed is greater or equal to the entry's scrape_interval
            if time_elapsed >= timedelta(minutes=entity["scrape_interval"]):
                self.logger.info(
                    f"Searching for: {entity['search_string']} on {entity['url']}"
                )
                # Perform the scraping task
                (
                    req_status,
                    req_status_detail,
                    req_html_content,
                ) = await self.is_string_within_element(
                    entity["url"],
                    entity["xpath"],
                    entity["search_string"],
                )

                # Update the PagePatrol entry with the last scrape event information
                entity["last_scrape_time"] = datetime.utcnow().replace(tzinfo=utc)
                entity["last_scrape_status"] = req_status
                entity["last_scrape_status_detail"] = req_status_detail
                entity["last_scrape_html_content"] = req_html_content

                # Update the PagePatrol entry in the table storage
                self.table_storage.update_entity(
                    self.table_storage.page_patrol_table_client,
                    mode=UpdateMode.REPLACE,
                    entity=entity,
                )

                self.patrol_history_mgmt.record_scrape_history(
                    entity["PartitionKey"],
                    entity["RowKey"],
                    entity["last_scrape_time"],
                    req_html_content,
                )

                # Log the result of processing each entry
                self.logger.info(
                    f"Processed entry '{entity['url']}' with status '{req_status_detail}'"
                )

    def get_baseurl_from(self, url: str):
        parsed_uri = urlparse(url)
        result = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
        return result
