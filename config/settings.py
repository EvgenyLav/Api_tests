import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise RuntimeError("BASE_URL environment variable is not set. Copy .env.example to .env and fill in the value.")

_parsed = urlparse(BASE_URL)
ROOT_URL = f"{_parsed.scheme}://{_parsed.netloc}"

RUN_TICKET_CREATION_CHECKS = os.getenv("RUN_TICKET_CREATION_CHECKS", "false").lower() == "true"

USER_LOGIN = os.getenv("USER_LOGIN", "")
USER_PASSWORD = os.getenv("USER_PASSWORD", "")