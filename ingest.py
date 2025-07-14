#
# =================================================================
#  Complete and Corrected Code for: ingest.py
# =================================================================
#
import os
import shutil
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, WebBaseLoader
import chromadb
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "openipc_knowledge"

#from app.config import DOCS_URL, GITHUB_REPOS 
from app.config import API_ID, API_HASH, SESSION_PATH, GITHUB_REPOS, DOCS_URL

# DOCS_URL = "https://docs.openipc.org/getting-started/homepage/"

# TARGET_CHATS = {
#     "OpenIPC equipment testers",
#     "OpenIPC FPV users",
#     # Add any other chat names you want to target here
# }

# GITHUB_REPOS = [
#     "https://github.com/OpenIPC/firmware.git",
#     "https://github.com/OpenIPC/docs.git"
#     # Add any other repository URLs here
# ]

REPO_PATH_BASE = "./temp_repos"

#REPO_PATH = "./temp_repo"

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
    # Loop through each repository URL in our list
    for repo_url in GITHUB_REPOS:
        try:
            # Create a unique path for each repo to avoid conflicts
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(REPO_PATH_BASE, repo_name)
            
            print(f"\n--- Processing repo: {repo_name} ---")

            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            Repo.clone_from(repo_url, to_path=repo_path)
            
            for root, _, files in os.walk(repo_path):
                for file in files:
                    # Add more extensions as needed
                    if file.endswith(('.c', '.h', '.py', 'Makefile', '.md', '.txt')):
                        file_path = os.path.join(root, file)
                        try:
                            loader = TextLoader(file_path, encoding='utf-8')
                            documents = loader.load()
                            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
                            chunks = text_splitter.split_documents(documents)
                            
                            if not chunks: continue

                            contents = [c.page_content for c in chunks]
                            # Add repo_name to the ID to ensure it's unique
                            ids = [f"github_{repo_name}_{file}_{i}" for i, _ in enumerate(chunks)]
                            collection.add(documents=contents, ids=ids)
                            print(f"  Added {len(chunks)} chunks from {file}")
                        except Exception as e:
                            print(f"  Skipping {file} due to error: {e}")
            
            # Clean up the individual repo directory after processing
            shutil.rmtree(repo_path)

        except Exception as e:
            print(f"  Failed to process repo {repo_url}. Error: {e}")

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