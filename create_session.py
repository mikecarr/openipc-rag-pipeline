from telethon.sync import TelegramClient
from dotenv import load_dotenv
import os

# Load variables from .env
load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone = os.getenv("TELEGRAM_PHONE")  # optional, in case you need it later

with TelegramClient("session", api_id, api_hash) as client:
    print("✅ Session created successfully.")
