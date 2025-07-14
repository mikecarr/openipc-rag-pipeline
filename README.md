
# AI Knowledge Base for OpenIPC

This project builds a complete, local-first AI knowledge base and chatbot for the OpenIPC project. It uses a **Retrieval-Augmented Generation (RAG)** pipeline to provide accurate answers based on a comprehensive set of data sources, including:

-   Telegram Chat Histories
-   GitHub Source Code Repositories
-   Official Documentation Websites

The system runs entirely on your local machine using Docker and a local LLM powered by Ollama, ensuring complete privacy and no API costs.

## Key Features

-   **Multi-Source Data Ingestion**: A powerful Python script (`ingest.py`) to scrape, process, and index data from multiple GitHub repos, websites, and your scraped Telegram chat logs.
-   **Local-First AI**: Uses Ollama to run powerful open-source models (like Llama 3) locally on your machine (optimized for Apple Silicon but works elsewhere).
-   **Vector Database for RAG**: Employs ChromaDB to store the knowledge base, allowing the AI to find the most relevant information before answering a question.
-   **Interactive Web UI**: A clean, modern web interface built with Vue.js for managing data sources and chatting with the AI.
-   **Fully Containerized**: The entire application stack (backend, databases, frontend) is managed with Docker and Docker Compose for easy setup and consistent operation.

## Architecture

The application consists of two main workflows: **Ingestion** and **Chat**.

#### Ingestion Flow (Populating the Knowledge Base)

```
(You) ----> Runs [ ingest.py ] script
                  |
                  |--- 1. Clones GitHub Repos
                  |--- 2. Scrapes Docs Website
                  |--- 3. Reads PostgreSQL DB (Telegram Chats)
                  |
                  +-----> Populates [ ChromaDB Vector Store ]
```

#### Chat Flow (Asking a Question)

```
(User) <--> [ Vue.js Frontend ] <--> [ FastAPI Backend ]
                                          |
      +-----------------------------------+----------------------------------+
      |                                   |                                  |
      v                                   v                                  v
[ PostgreSQL DB ]                 [ ChromaDB Vector Store ]            [ Ollama (Llama 3) ]
(For Chat List)                   (Retrieves Context)                  (Generates Answer)
```

---

## Setup and Installation

Follow these steps to get the entire system running on your local machine.

### Prerequisites

1.  **Docker & Docker Compose**: Ensure they are installed on your system. [Install Docker](https://docs.docker.com/get-docker/).
2.  **Python**: Python 3.11+ installed on your host machine for running the ingestion script.
3.  **Git**: Required for cloning this repository and the data source repositories.
4.  **Ollama**: The engine for running the local LLM.
    -   Go to [https://ollama.com](https://ollama.com) and download/install the application for your OS.
    -   Run the Ollama application. You should see a llama icon in your menu bar.
    -   **Important**: Pull the model you intend to use. Open your terminal and run:
        ```bash
        ollama run llama3:8b-instruct-q4_K_M
        ```

### Installation Steps

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Set Up Environment Variables**
    Create a `.env` file for your Telegram API credentials. You can copy the example file to start.
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file and fill in your actual Telegram `API_ID`, `API_HASH`, and `PHONE`.
    ```ini
    # .env
    TELEGRAM_API_ID=1234567
    TELEGRAM_API_HASH=your_api_hash_here
    TELEGRAM_PHONE=+15551234567
    ```

3.  **Build and Run the Docker Services**
    This command will build the images for the frontend and backend, and start all the services (FastAPI Backend, PostgreSQL DB, ChromaDB, Vue Frontend).
    ```bash
    docker-compose up -d --build
    ```

4.  **Install Python Dependencies for Ingestion**
    The ingestion script runs on your host machine. Install its dependencies into a local virtual environment.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

5.  **Run the Knowledge Base Ingestion**
    This is the final setup step. Run the ingestion script to populate your ChromaDB vector store with data from GitHub and the documentation website.
    ```bash
    python ingest.py
    ```
    This script is safe to run multiple times. It will only add new information to the knowledge base.

---

## How to Use the Application

1.  **Access the Web UI**: Open your browser and navigate to `http://localhost:5173`.

2.  **Scrape Telegram Chats (Optional)**:
    -   The left "Data Sources" panel lists your Telegram chats.
    -   To add a specific chat's history to your PostgreSQL database, click the "Scrape" button next to it.
    -   After scraping, re-run the `python ingest.py` script to add the new messages to your AI's knowledge base.

3.  **Chat with the AI**:
    -   The main window on the right is your chat interface.
    -   Type a question about OpenIPC into the input box at the bottom and press Enter.
    -   The AI will use its entire knowledge base (GitHub, Docs, and scraped chats) to formulate and stream back an answer.

#### Example Questions:
-   "How do I set up the firmware for the FPV-Thinker-AIO?"
-   "What is the purpose of the `xmdp.c` file?"
-   "What are the contribution guidelines for this project?"

---

## Project Structure

```
.
├── app/                  # FastAPI Backend Source Code
│   ├── main.py           # Main API logic (chat, scrape endpoints)
│   └── scraper.py        # Telegram scraper logic
├── data/                 # Stores Telegram session file
├── db/                   # PostgreSQL initialization scripts
├── frontend/             # Vue.js Frontend Source Code
│   └── chatbot-ui/
│       ├── src/
│       │   ├── components/
│       │   │   └── ChatUI.vue  # The main UI component
│       │   ├── api.js          # Frontend API functions
│       │   └── App.vue         # Root Vue component
│       └── Dockerfile          # Dockerfile for the frontend
├── .env.example          # Template for environment variables
├── docker-compose.yml    # Defines all services, networks, and volumes
├── Dockerfile            # Dockerfile for the backend
├── ingest.py             # Script to populate the knowledge base
└── requirements.txt      # Python dependencies
```

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.



## Inject Data
python ingest.py                             
--- Starting Knowledge Base Ingestion ---


https://ollama.com/library/llama3/

brew services start ollama

# download could take a while
ollama run llama3:8b-instruct-q4_K_M