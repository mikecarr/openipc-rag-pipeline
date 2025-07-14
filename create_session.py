from telethon.sync import TelegramClient

API_ID = 22795079  # Replace with your real API ID
API_HASH = "31d8aec0e12cab8dd9214efbfd8f4175"

with TelegramClient("session", API_ID, API_HASH) as client:
    print("✅ Session created successfully.")
