import os
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")
PIPEDRIVE_PIPELINE_ID = os.getenv("PIPEDRIVE_PIPELINE_ID") or None
PIPEDRIVE_STAGE_ID = os.getenv("PIPEDRIVE_STAGE_ID") or None

APOLLO_BASE_URL = "https://api.apollo.io/v1"
PIPEDRIVE_BASE_URL = "https://api.pipedrive.com/v1"
