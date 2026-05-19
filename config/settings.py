import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://testapi.intercars.ru/api/v1")
RUN_TICKET_CREATION_CHECKS = os.getenv("RUN_TICKET_CREATION_CHECKS", "false").lower() == "true"