from urllib.parse import urlparse

from scrapy import Selector
from scrapy.spiders import Spider


class XpathSpider(Spider):
    name = "xpath_spider"

    def __init__(self, **request):
        try:
            self.url = request["url"]
            self.xpath = request["xpath"]
            self.search_string = request["search_string"]
            self.base_url = get_baseurl_from(self.url)
        except Exception as e:
            raise Exception(f"{str(e)} Request data is incomplete")

        super(XpathSpider, self).__init__()
        self.start_urls = [self.url]

    def parse(self, response, **kwargs):
        web_element = response.xpath(self.xpath)
        # Find web element
        if not web_element:
            yield {
                "status": "web_element_not_found",
                "status_detail": f"Could not find any web element from xpath: {self.xpath}"
                f" Please double check the xpath.",
                "html_content": "",
            }
        if len(web_element.getall()) > 1:
            yield {
                "status": "multiple_elements_found",
                "status_detail": f"More than one web element found from xpath: {self.xpath}"
                f" Please provide an xpath for a unique web element.",
                "html_content": "",
            }

        # Check if string exists within the web element
        if self.search_string_in_elements(web_element):
            html_content = web_element.extract_first().replace(
                'href="/', f'href="{self.base_url}/'
            )
            print(html_content)
            yield {
                "status": "found",
                "status_detail": "Found string within the web element.",
                "html_content": html_content,
            }
        else:
            yield {
                "status": "string_not_found",
                "status_detail": "Did not find the string within the web element.",
                "html_content": "",
            }

    def is_a_string_within_webelement(self, web_element):
        sel = Selector(text=web_element.get()).xpath("//*")
        if (
            len(sel.xpath(f"//*[contains(text(), '{self.search_string}')]").getall())
            > 0
        ):
            return True

    def search_string_in_elements(self, element):
        if self.is_a_string_within_webelement(element):
            return True
        else:
            for child_element in element.xpath(".//*"):
                if self.is_a_string_within_webelement(child_element):
                    return True
        return False


def get_baseurl_from(url):
    parsed_uri = urlparse(url)
    result = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
    return result
