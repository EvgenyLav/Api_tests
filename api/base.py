import requests
import logging

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class BaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        logger.info(f"[REQUEST] GET {url} | params: {kwargs.get('params')}")
        response = self.session.get(url, **kwargs)
        logger.info(f"[RESPONSE] Status: {response.status_code} | Body: {response.text}")
        return response

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        logger.info(f"[REQUEST] POST {url} | payload: {kwargs.get('json')}")
        response = self.session.post(url, **kwargs)
        logger.info(f"[RESPONSE] Status: {response.status_code} | Body: {response.text}")
        return response