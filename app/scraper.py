from telethon import TelegramClient
from app.config import API_ID, API_HASH, SESSION_PATH

client = TelegramClient(SESSION_PATH, API_ID, API_HASH)

from telethon.tl.types import Channel

async def fetch_messages(client, chat, limit):
    
    channel_id = chat if chat == "me" else int(chat)

    dialogs = await client.get_dialogs()

    channel_entity = None
    for dialog in dialogs:
        if isinstance(dialog.entity, Channel) and dialog.entity.id == channel_id:
            channel_entity = dialog.entity
            break

    if channel_entity is None:
        raise ValueError(f"Channel with id {channel_id} not found in dialogs")

    messages = []
    async for message in client.iter_messages(channel_entity, limit=limit):
        # Convert message to JSON-serializable dict
        messages.append({
            "id": message.id,
            "date": message.date.isoformat() if message.date else None,
            "text": message.message,
            "sender_id": message.sender_id,
            "media": str(message.media) if message.media else None,
            # Add other fields you want to expose here
        })

    return messages
