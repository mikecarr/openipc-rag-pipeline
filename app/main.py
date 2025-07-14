#
# =================================================================
#  Complete and Corrected Code for: app/main.py
# =================================================================
#
import os
import asyncio
from datetime import datetime

import sqlalchemy
import ollama
from databases import Database
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert

from scraper import fetch_messages, client # Assuming scraper.py exists and is correct

# --- Configuration ---
DATABASE_URL = "postgresql://postgres:password@db:5432/telegramdb"

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str

# --- FastAPI App Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
database = Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

messages_table = sqlalchemy.Table(
    "messages",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.BigInteger, primary_key=True),
    sqlalchemy.Column("chat_id", sqlalchemy.BigInteger, nullable=False),
    sqlalchemy.Column("sender_id", sqlalchemy.BigInteger, nullable=False),
    sqlalchemy.Column("date", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("text", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("media", sqlalchemy.JSON, nullable=True),
)

# --- AI Model Client Setup ---
try:
    ollama_client = ollama.Client(host='http://host.docker.internal:11434')
    print("Successfully configured Ollama client.")
except Exception as e:
    print(f"FATAL: Could not configure Ollama client. Is Ollama running on the host? Error: {e}")
    ollama_client = None


# --- App Lifecycle Events ---
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# --- Helper Functions ---
async def ensure_client_connected():
    if not client.is_connected():
        await client.start()

async def save_message(message, chat_id):
    stmt = insert(messages_table).values(
        id=message["id"],
        chat_id=chat_id,
        sender_id=message["sender_id"],
        date=datetime.fromisoformat(message["date"]) if message["date"] else None,
        text=message["text"],
        media=message["media"],
    )
    do_nothing_stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
    try:
        await database.execute(do_nothing_stmt)
    except Exception as e:
        print(f"Unexpected DB error for message {message['id']}: {e}")


# --- API Endpoints ---
@app.get("/chats")
async def list_chats():
    await ensure_client_connected()
    dialogs = await client.get_dialogs()
    chat_ids = [getattr(d.entity, "id", None) for d in dialogs]
    valid_chat_ids = [cid for cid in chat_ids if cid is not None]

    if not valid_chat_ids:
        counts = {}
    else:
        query = (
            sqlalchemy.select(
                messages_table.c.chat_id,
                sqlalchemy.func.count(messages_table.c.id).label("count")
            )
            .where(messages_table.c.chat_id.in_(valid_chat_ids))
            .group_by(messages_table.c.chat_id)
        )
        rows = await database.fetch_all(query)
        counts = {row['chat_id']: row['count'] for row in rows}

    response_chats = []
    for dialog in dialogs:
        chat_id = getattr(dialog.entity, "id", None)
        response_chats.append({
            "name": dialog.name,
            "id": chat_id,
            "username": getattr(dialog.entity, "username", None),
            "type": type(dialog.entity).__name__,
            "message_count": counts.get(chat_id, 0)
        })
    return response_chats

@app.post("/chats/{chat_id}/scrape")
async def scrape_and_save_chat_messages(chat_id: int, limit: int = 100):
    await ensure_client_connected()
    print(f"SCRAPING: Starting scrape for chat_id: {chat_id}")
    try:
        scraped_messages = await fetch_messages(client, chat_id, limit)
    except Exception as e:
        print(f"SCRAPING ERROR: Could not fetch messages for chat {chat_id}. Reason: {e}")
        return {"status": "error", "messages_saved": 0, "detail": str(e)}

    count = 0
    for msg_dict in scraped_messages:
        await save_message(msg_dict, chat_id)
        count += 1
    
    print(f"SCRAPING: Finished. Saved {count} new messages for chat_id: {chat_id}")
    return {"status": "success", "messages_saved": count}

@app.post("/chats/{chat_id}/chat")
async def handle_chat(chat_id: int, request: ChatRequest):
    if not ollama_client:
        async def error_stream():
            yield "Error: Local AI model not configured."
        return StreamingResponse(error_stream(), media_type="text/plain")

    query = (
        messages_table.select()
        .with_only_columns(messages_table.c.text)
        .where(messages_table.c.chat_id == chat_id)
        .where(messages_table.c.text.isnot(None))
        .order_by(messages_table.c.date.asc())
    )
    rows = await database.fetch_all(query)
    conversation_text = "\n".join([row['text'] for row in rows])

    system_prompt = (
        "You are a helpful AI assistant. Your knowledge is strictly limited to the "
        "contents of the chat log provided below. Answer the user's question based ONLY "
        "on this information. Do not use any external knowledge. If the answer is not "
        "in the chat log, state that clearly."
    )
    
    full_prompt = (
        f"--- CHAT LOG CONTEXT ---\n"
        f"{conversation_text}\n"
        f"--- END OF CHAT LOG ---\n\n"
        f"User Question: {request.query}"
    )

    async def stream_generator():
        try:
            print("CHATBOT: Sending context to local Llama 3 model...")
            stream = ollama_client.chat(
                model='llama3:8b-instruct-q4_K_M',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': full_prompt}
                ],
                stream=True
            )
            print("CHATBOT: Receiving stream from model...")
            for chunk in stream:
                yield chunk['message']['content']
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"ERROR: Ollama stream failed: {e}")
            yield "Error communicating with the local AI model."

    return StreamingResponse(stream_generator(), media_type="text/plain")