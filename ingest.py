#
# =================================================================
#  Complete and Corrected Code for: ingest.py
# =================================================================
#
import os
import shutil
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter
# CHANGE #1: Import WebBaseLoader instead of BSHTMLLoader
from langchain_community.document_loaders import TextLoader, WebBaseLoader
import chromadb
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "openipc_knowledge"
DOCS_URL = "https://docs.openipc.org/getting-started/homepage/"
GITHUB_REPO_URL = "https://github.com/OpenIPC/firmware.git"
REPO_PATH = "./temp_repo"

# --- Helper Functions ---
def get_all_site_links(url, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()
    if url in visited_urls:
        return visited_urls
    
    print(f"Discovering: {url}")
    visited_urls.add(url)

    try:
        domain_name = urlparse(url).netloc
        soup = BeautifulSoup(requests.get(url).content, "html.parser")
        for a_tag in soup.find_all("a"):
            href = a_tag.attrs.get("href")
            if href == "" or href is None:
                continue
            href = urljoin(url, href)
            href = href.split('#')[0].split('?')[0]
            if domain_name in href and href not in visited_urls:
                get_all_site_links(href, visited_urls)
    except Exception as e:
        print(f"  Could not discover links on {url}: {e}")

    return visited_urls

# --- Main Ingestion Logic ---
if __name__ == "__main__":
    print("--- Starting Knowledge Base Ingestion ---")
    
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    # Delete the collection if it already exists to start fresh
    # print(f"Resetting collection: {COLLECTION_NAME}")
    # client.delete_collection(name=COLLECTION_NAME)
    
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Ingest GitHub Repository
    print(f"\n--- Ingesting GitHub Repo: {GITHUB_REPO_URL} ---")
    if os.path.exists(REPO_PATH):
        shutil.rmtree(REPO_PATH)
    Repo.clone_from(GITHUB_REPO_URL, to_path=REPO_PATH)
    
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            if file.endswith(('.c', '.h', '.py', 'Makefile', '.md', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
                    chunks = text_splitter.split_documents(documents)
                    
                    if not chunks: continue

                    # The content of each chunk is in the `page_content` attribute
                    contents = [c.page_content for c in chunks]
                    ids = [f"github_{file}_{i}" for i, _ in enumerate(chunks)]
                    collection.add(documents=contents, ids=ids)
                    print(f"  Added {len(chunks)} chunks from {file}")
                except Exception as e:
                    print(f"  Skipping {file} due to error: {e}")

    # 3. Ingest Documentation Website
    print(f"\n--- Ingesting Docs Website: {DOCS_URL} ---")
    all_links = get_all_site_links(DOCS_URL)
    
    # CHANGE #2: Use WebBaseLoader and fix the collection.add call
    for link in all_links:
        try:
            print(f"Loading content from: {link}")
            loader = WebBaseLoader(link)
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)

            if not chunks: continue
            
            # The content of each chunk is in the `page_content` attribute
            contents = [c.page_content for c in chunks]
            ids = [f"docs_{link.replace('/', '_')}_{i}" for i, _ in enumerate(chunks)]
            collection.add(documents=contents, ids=ids)
            print(f"  Added {len(chunks)} chunks from {link}")
        except Exception as e:
            print(f"  Skipping {link} due to error: {e}")

    print("\n--- Ingestion Complete! ---")