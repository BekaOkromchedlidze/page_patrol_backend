from datetime import datetime, timedelta

import scrapydo
from azure.data.tables import UpdateMode
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.spiders.xpath_spider import XpathSpider

from ..table_storage import website_monitoring_table_client

router = APIRouter()


# Given url, element_xpath and search_string, search for search_string within the element and return its HTML if found.
async def is_string_within_element(url: str, element_xpath: str, search_string: str):
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


def get_response(status_code, status_detail, html_content):
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": status_detail,
            "data": {"html": html_content},
        },
    )


@router.get("/web-scraper/html", status_code=status.HTTP_200_OK)
async def get_element_html(url: str, element_xpath: str, search_string: str):

    req_status, req_status_detail, req_html_content = await is_string_within_element(
        url, element_xpath, search_string
    )

    status_map = {
        "found": status.HTTP_200_OK,
        "web_element_not_found": status.HTTP_400_BAD_REQUEST,
        "multiple_elements_found": status.HTTP_400_BAD_REQUEST,
        "string_not_found": status.HTTP_404_NOT_FOUND,
    }

    return get_response(
        status_map.get(req_status, status.HTTP_500_INTERNAL_SERVER_ERROR),
        req_status_detail,
        req_html_content,
    )


async def process_website_monitor():
    now = datetime.utcnow()

    # Get all enabled and not deleted website_monitor entries
    entries = website_monitoring_table_client.query_entities(
        query_filter="is_enabled eq true and is_deleted eq false"
    )

    for entry in entries:
        # Calculate the elapsed time since the last scrape attempt
        last_scrape_time = entry.get("last_scrape_time", None)
        if last_scrape_time:
            time_elapsed = now - last_scrape_time
        else:
            time_elapsed = timedelta(minutes=entry["scrape_interval"])

        # Check if the time elapsed is greater or equal to the entry's scrape_interval
        if time_elapsed >= timedelta(minutes=entry["scrape_interval"]):
            # Perform the scraping task
            (
                req_status,
                req_status_detail,
                req_html_content,
            ) = await is_string_within_element(
                entry["url"], entry["xpath"], entry["search_string"]
            )

            # Update the WebsiteMonitor entry with the last scrape event information
            entry["last_scrape_time"] = datetime.utcnow()
            entry["last_scrape_status"] = req_status
            entry["last_scrape_status_detail"] = req_status_detail
            entry["last_scrape_html_content"] = req_html_content

            # Update the WebsiteMonitor entry in the table storage
            website_monitoring_table_client.update_entity(
                mode=UpdateMode.REPLACE, entity=entry
            )
