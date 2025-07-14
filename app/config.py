# app/config.py
import os

# --- Knowledge Base Sources ---
DOCS_URL = "https://docs.openipc.org/getting-started/homepage/"

TARGET_CHATS = {
    "OpenIPC equipment testers",
    "OpenIPC FPV users",
}
GITHUB_REPOS = [
    "https://github.com/OpenIPC/firmware.git",
    "https://github.com/OpenIPC/docs.git",
    "https://github.com/OpenIPC/builder.git",
    "https://github.com/OpenIPC/msposd.git",
    "https://github.com/OpenIPC/adaptive-link.git",
    "https://github.com/OpenIPC/PixelPilot"
]

# --- Telegram Credentials from Environment ---
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
PHONE = os.environ.get("TELEGRAM_PHONE")

# Define session path consistently
SESSION_PATH = "data/session"