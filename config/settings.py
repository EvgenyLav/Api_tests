import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise RuntimeError("BASE_URL environment variable is not set. Copy .env.example to .env and fill in the value.")

RUN_TICKET_CREATION_CHECKS = os.getenv("RUN_TICKET_CREATION_CHECKS", "false").lower() == "true"