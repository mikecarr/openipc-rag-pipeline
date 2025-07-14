from telethon.sync import TelegramClient
from configparser import ConfigParser

# Option 1: Hardcoded
# API_ID = 123456  # your API ID
# API_HASH = "your_api_hash"

# Option 2 (better): Read from env or config
import os
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION = "data/session"  # or your exact session file prefix

with TelegramClient(SESSION, API_ID, API_HASH) as client:
    print("🔍 Fetching chats...")
    dialogs = client.get_dialogs()

    for i, dialog in enumerate(dialogs, 1):
        name = dialog.name or "Unnamed"
        id_or_username = getattr(dialog.entity, "username", None) or dialog.entity.id
        chat_type = type(dialog.entity).__name__
        print(f"{i:2}. {name}  ({chat_type}) → {id_or_username}")
