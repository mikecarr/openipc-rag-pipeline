#
# =================================================================
#  Complete and Updated Code for: ingest.py (with Stats)
# =================================================================
#
import os
import shutil
import time  # NEW: Import the time module
from git import Repo
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, WebBaseLoader
import chromadb
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---
# Note: This now correctly imports DOCS_URLS (plural)
from app.config import GITHUB_REPOS, DOCS_URLS

CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "openipc_knowledge"
REPO_PATH_BASE = "./temp_repos"

# --- Helper Functions ---
def get_all_site_links(url, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()
    if url in visited_urls:
        return visited_urls
    
    # We print "Discovering" here, but will count "Processing" later for stats
    # print(f"Discovering: {url}") 
    visited_urls.add(url)

    try:
        domain_name = urlparse(url).netloc
        soup = BeautifulSoup(requests.get(url, timeout=10).content, "html.parser")
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
    
    # --- NEW: Initialize Stats Counters and Timer ---
    start_time = time.time()
    stats = {
        "repos_processed": 0,
        "files_processed": 0,
        "sites_processed": 0,
        "chunks_added": 0,
    }
    # ----------------------------------------------

    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    initial_vector_count = collection.count()
    print(f"Vector DB contains {initial_vector_count} vectors before ingestion.")
    
    # 2. Ingest GitHub Repositories
    print(f"\n--- Ingesting {len(GITHUB_REPOS)} GitHub Repositories ---")
    for repo_url in GITHUB_REPOS:
        try:
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(REPO_PATH_BASE, repo_name)
            
            print(f"\n--- Processing repo: {repo_name} ---")

            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
            Repo.clone_from(repo_url, to_path=repo_path)
            
            repo_file_count = 0
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(('.c', '.h', '.py', 'Makefile', '.md', '.txt')):
                        stats["files_processed"] += 1 # Increment file counter
                        repo_file_count += 1
                        file_path = os.path.join(root, file)
                        try:
                            loader = TextLoader(file_path, encoding='utf-8')
                            documents = loader.load()
                            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
                            chunks = text_splitter.split_documents(documents)
                            
                            if not chunks: continue

                            contents = [c.page_content for c in chunks]
                            ids = [f"github_{repo_name}_{file}_{i}" for i, _ in enumerate(chunks)]
                            collection.add(documents=contents, ids=ids)
                            stats["chunks_added"] += len(chunks) # Increment chunk counter
                            # print(f"  Added {len(chunks)} chunks from {file}")
                        except Exception as e:
                            print(f"  Skipping {file} due to error: {e}")
            
            print(f"Processed {repo_file_count} files from {repo_name}.")
            stats["repos_processed"] += 1 # Increment repo counter
            shutil.rmtree(repo_path)
        except Exception as e:
            print(f"  Failed to process repo {repo_url}. Error: {e}")

    # 3. Ingest Documentation Websites
    print(f"\n--- Ingesting {len(DOCS_URLS)} Documentation Website(s) ---")
    all_docs_links = set()
    for start_url in DOCS_URLS:
        print(f"Discovering links starting from: {start_url}")
        all_docs_links.update(get_all_site_links(start_url))

    print(f"\nFound a total of {len(all_docs_links)} unique documentation pages to process.")
    for link in all_docs_links:
        try:
            stats["sites_processed"] += 1 # Increment site counter
            # print(f"Loading content from: {link}")
            loader = WebBaseLoader(link)
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)

            if not chunks: continue
            
            contents = [c.page_content for c in chunks]
            ids = [f"docs_{link.replace('/', '_')}_{i}" for i, _ in enumerate(chunks)]
            collection.add(documents=contents, ids=ids)
            stats["chunks_added"] += len(chunks) # Increment chunk counter
            # print(f"  Added {len(chunks)} chunks from {link}")
        except Exception as e:
            print(f"  Skipping {link} due to error: {e}")

    # --- NEW: Final Summary Report ---
    end_time = time.time()
    duration = end_time - start_time
    final_vector_count = collection.count()

    print("\n" + "="*50)
    print("--- INGESTION COMPLETE: SUMMARY ---")
    print(f"Total Time Taken: {duration:.2f} seconds")
    print("-"*50)
    print("Sources Processed:")
    print(f"  - GitHub Repositories: {stats['repos_processed']} / {len(GITHUB_REPOS)}")
    print(f"  - Total Files Indexed: {stats['files_processed']}")
    print(f"  - Web Pages Indexed:   {stats['sites_processed']} / {len(all_docs_links)}")
    print("-"*50)
    print("Database Statistics:")
    print(f"  - Initial Vector Count: {initial_vector_count}")
    print(f"  - Chunks Added This Run: {stats['chunks_added']}")
    print(f"  - Final Vector Count:   {final_vector_count}")
    print("="*50 + "\n")