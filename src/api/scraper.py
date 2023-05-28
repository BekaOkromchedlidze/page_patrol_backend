import logging
from datetime import datetime, timedelta

import pytz
import scrapydo
from azure.data.tables import UpdateMode
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.api.patrol_history_mgmt import PatrolHistoryManagement
from src.logger_config import setup_logger
from src.spiders.xpath_spider import XpathSpider
from src.table_storage import TableStorage


class Scraper:
    def __init__(
        self, table_storage: TableStorage, patrol_history_mgmt: PatrolHistoryManagement
    ):
        self.router = APIRouter()
        self.logger = setup_logger(__name__)
        self.table_storage = table_storage
        self.router.get("/scraper/html", status_code=status.HTTP_200_OK)(
            self.is_string_within_element
        )
        self.patrol_history_mgmt = patrol_history_mgmt

    # Given url, element_xpath and search_string, search for search_string within the element and return its HTML if found.
    async def is_string_within_element(
        self, url: str, element_xpath: str, search_string: str
    ):
        scrapydo.setup()

        spider_result = scrapydo.run_spider(
            XpathSpider, url=url, xpath=element_xpath, search_string=search_string
        )[  # type: ignore
            0
        ]

        req_status = spider_result.get("status")
        req_status_detail = spider_result.get("status_detail")
        req_html_content = spider_result.get("html_content")

        return req_status, req_status_detail, req_html_content

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
            self.logger.info(
                f"Searching for: {entity['search_string']} on {entity['url']}"
            )

            # Calculate the elapsed time since the last scrape attempt
            last_scrape_time = entity.get("last_scrape_time", None)
            if last_scrape_time:
                time_elapsed = now - last_scrape_time
            else:
                time_elapsed = timedelta(minutes=entity["scrape_interval"])

            # Check if the time elapsed is greater or equal to the entry's scrape_interval
            if time_elapsed >= timedelta(minutes=entity["scrape_interval"]):
                # Perform the scraping task
                (
                    req_status,
                    req_status_detail,
                    req_html_content,
                ) = await self.is_string_within_element(
                    entity["url"], entity["xpath"], entity["search_string"]
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
                    entity["RowKey"],
                    entity["last_scrape_time"],
                    req_html_content,
                )

                # Log the result of processing each entry
                self.logger.info(
                    f"Processed entry '{entity['url']}' with status '{req_status_detail}'"
                )
