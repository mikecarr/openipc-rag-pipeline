#
# =================================================================
#  FINAL RAG-Enabled Code for: app/main.py
# =================================================================
#
import os
import asyncio
from datetime import datetime

import sqlalchemy
import ollama
import chromadb # NEW: Import chromadb
from databases import Database
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert

from app.scraper import fetch_messages, client
from app.config import DOCS_URL, GITHUB_REPOS, TARGET_CHATS

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

# --- AI & Knowledge Base Client Setup ---
try:
    ollama_client = ollama.Client(host='http://host.docker.internal:11434')
    print("Successfully configured Ollama client.")
except Exception as e:
    print(f"FATAL: Could not configure Ollama client. Is Ollama running on the host? Error: {e}")
    ollama_client = None

# NEW: Configure the ChromaDB client to connect to the 'chroma' service
try:
    chroma_client = chromadb.HttpClient(host='chroma', port=8000)
    
    collection = chroma_client.get_or_create_collection("openipc_knowledge")
    
    print("Successfully connected to ChromaDB knowledge base.")
except Exception as e:
    print(f"FATAL: Could not connect to ChromaDB. Is it running? Is the 'openipc_knowledge' collection created? Error: {e}")
    collection = None

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
    """
    Fetches dialogs from Telegram, but only returns the ones
    specified in the TARGET_CHATS set.
    """
    await ensure_client_connected()
    dialogs = await client.get_dialogs()
    
    # Filter the dialogs to only include those in our target list
    target_dialogs = [d for d in dialogs if d.name in TARGET_CHATS]
    
    chat_ids = [getattr(d.entity, "id", None) for d in target_dialogs]
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
    for dialog in target_dialogs:
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
    # This function remains the same
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

# MODIFIED: The chat endpoint now uses the RAG pattern
@app.post("/chat")
async def handle_rag_chat(request: ChatRequest):
    if not ollama_client or not collection:
        async def error_stream():
            yield "Error: AI or Knowledge Base is not configured on the server."
        return StreamingResponse(error_stream(), media_type="text/plain")

    user_query = request.query.lower()
    context_documents = ""
    
    # --- NEW META-AWARENESS LOGIC ---
    meta_keywords = ["what do you know", "how many messages", "your knowledge", "what repos", "what sources"]
    
    if any(keyword in user_query for keyword in meta_keywords):
        print("META_QUERY DETECTED: Gathering knowledge base stats...")
        stats = await get_knowledge_base_stats()
        
        # Format the stats into a text block for the AI
        stats_context = "I have been provided with the following information about my own knowledge base:\n\n"
        stats_context += f"- My knowledge base contains a total of {stats['vector_db_count']} document chunks.\n"
        stats_context += f"- I have knowledge from the documentation site: {stats['docs_url']}\n"
        stats_context += "- I have knowledge from these GitHub repositories:\n"
        for repo in stats['github_repos']:
            stats_context += f"  - {repo}\n"
        
        stats_context += "- I have knowledge from these scraped Telegram chats:\n"
        for chat_id, chat_data in stats['telegram_chats'].items():
            stats_context += f"  - Chat ID {chat_id}: Contains {chat_data['message_count']} messages, ranging from {chat_data['earliest']} to {chat_data['latest']}.\n"
        
        context_documents = stats_context
    else:
        # --- This is the original RAG logic ---
        try:
            print(f"RAG: Querying knowledge base for: '{request.query}'")
            results = collection.query(query_texts=[request.query], n_results=7)
            if results['documents'] and results['documents'][0]:
                context_documents = "\n---\n".join(results['documents'][0])
                print(f"RAG: Found {len(results['documents'][0])} relevant document chunks.")
            else:
                print("RAG: Found 0 relevant document chunks.")
        except Exception as e:
            print(f"RAG Error: {e}")
            # We'll just proceed with an empty context if the query fails

    # --- The rest of the function remains the same ---
    system_prompt = (
        "You are an expert AI assistant for the OpenIPC project. "
        "You will be given a user's question and a set of context documents from your knowledge base. "
        "Your task is to synthesize an answer to the question based *only* on the provided context. "
        "If the context does not contain the answer, explicitly state that the information is not in the knowledge base."
    )
    
    full_prompt = (
        f"--- CONTEXT DOCUMENTS ---\n"
        f"{context_documents if context_documents else 'No relevant documents were found.'}\n"
        f"--- END OF CONTEXT ---\n\n"
        f"Based ONLY on the context above, answer this question: {request.query}"
    )

    async def stream_generator():
        try:
            stream = ollama_client.chat(
                model='llama3:8b-instruct-q4_K_M',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': full_prompt}
                ],
                stream=True
            )
            for chunk in stream:
                yield chunk['message']['content']
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"ERROR: Ollama stream failed: {e}")
            yield "Error communicating with the local AI model."

    return StreamingResponse(stream_generator(), media_type="text/plain")

@app.get("/sources")
async def get_knowledge_sources():
    """Returns the list of configured data sources."""
    return {
        "docs_url": DOCS_URL,
        "github_repos": GITHUB_REPOS,
        "target_chats": list(TARGET_CHATS) # Convert set to list for JSON
    }
    
    
async def get_knowledge_base_stats():
    """Gathers statistics about the contents of the knowledge base."""
    stats = {
        "github_repos": GITHUB_REPOS,
        "docs_url": DOCS_URL,
        "telegram_chats": {},
        "vector_db_count": 0,
    }
    
    # 1. Get stats from PostgreSQL
    try:
        if database.is_connected:
            query = """
                SELECT chat_id, COUNT(id) as message_count, MIN(date) as earliest, MAX(date) as latest
                FROM messages
                GROUP BY chat_id
            """
            rows = await database.fetch_all(query)
            for row in rows:
                stats["telegram_chats"][row['chat_id']] = {
                    "message_count": row['message_count'],
                    "earliest": row['earliest'].strftime("%Y-%m-%d"),
                    "latest": row['latest'].strftime("%Y-%m-%d"),
                }
    except Exception as e:
        print(f"Could not fetch stats from PostgreSQL: {e}")

    # 2. Get stats from ChromaDB
    try:
        if collection:
            stats["vector_db_count"] = collection.count()
    except Exception as e:
        print(f"Could not fetch count from ChromaDB: {e}")
        
    return stats