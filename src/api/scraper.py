import scrapydo
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.spiders.xpath_spider import XpathSpider

router = APIRouter()


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
    """Given url, element_xpath and search_string, search for search_string within the element and return its HTML if
    found."""
    scrapydo.setup()

    spider_result = scrapydo.run_spider(
        XpathSpider, url=url, xpath=element_xpath, search_string=search_string
    )[  # type: ignore
        0
    ]

    req_status = spider_result.get("status")
    req_status_detail = spider_result.get("status_detail")
    req_html_content = spider_result.get("html_content")

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
