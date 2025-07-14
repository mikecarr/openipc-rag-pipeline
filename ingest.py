# ingest.py
import os
import shutil
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain.document_loaders import TextLoader, BSHTMLLoader
import chromadb
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "openipc_knowledge"
DOCS_URL = "https://docs.openipc.org/getting-started/homepage/"
GITHUB_REPO_URL = "https://github.com/OpenIPC/firmware.git" # Example repo
REPO_PATH = "./temp_repo"

# --- Helper Functions ---
def get_all_site_links(url):
    urls = set()
    domain_name = urlparse(url).netloc
    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")
        if href == "" or href is None or not href.startswith("/"):
            continue
        href = urljoin(url, href)
        if domain_name in href and href not in urls:
            urls.add(href)
            print(f"Discovered: {href}")
            urls.update(get_all_site_links(href)) # Recursive call
    return urls

# --- Main Ingestion Logic ---
if __name__ == "__main__":
    print("--- Starting Knowledge Base Ingestion ---")
    
    # 1. Initialize ChromaDB client
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Ingest GitHub Repository
    print(f"\n--- Ingesting GitHub Repo: {GITHUB_REPO_URL} ---")
    if os.path.exists(REPO_PATH):
        shutil.rmtree(REPO_PATH)
    Repo.clone_from(GITHUB_REPO_URL, to_path=REPO_PATH)
    
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            # Add more extensions as needed
            if file.endswith(('.c', '.h', '.py', 'Makefile', '.md', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
                    chunks = text_splitter.split_documents(documents)
                    
                    ids = [f"github_{file}_{i}" for i, _ in enumerate(chunks)]
                    collection.add(documents=chunks, ids=ids)
                    print(f"  Added {len(chunks)} chunks from {file}")
                except Exception as e:
                    print(f"  Skipping {file} due to error: {e}")

    # 3. Ingest Documentation Website
    print(f"\n--- Ingesting Docs Website: {DOCS_URL} ---")
    all_links = get_all_site_links(DOCS_URL)
    for link in all_links:
        try:
            loader = BSHTMLLoader(link)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)
            
            ids = [f"docs_{link.replace('/', '_')}_{i}" for i, _ in enumerate(chunks)]
            collection.add(documents=chunks, ids=ids)
            print(f"  Added {len(chunks)} chunks from {link}")
        except Exception as e:
            print(f"  Skipping {link} due to error: {e}")

    # Note: Ingesting Telegram chats would follow the same pattern.
    # You would connect to your PostgreSQL DB, fetch messages,
    # and add them to the collection with IDs like `telegram_{chat_id}_{msg_id}`.

    print("\n--- Ingestion Complete! ---")