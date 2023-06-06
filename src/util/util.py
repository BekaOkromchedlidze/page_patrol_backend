from urllib.parse import urlparse


class Utils:
    @staticmethod
    def get_baseurl_from(url: str):
        parsed_uri = urlparse(url)
        result = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
        return result
