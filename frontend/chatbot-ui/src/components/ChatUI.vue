<template>
  <div class="chat-container">
    <div class="chat-list">
      <h1>OpenIPC Chatbot</h1>
      <!-- MODIFIED: Knowledge Sources are now dynamic -->
      <div class="knowledge-sources">
        <h2>Knowledge Sources</h2>
        <div class="source-item">
          <span class="source-type">Docs:</span>
          <a :href="sources.docs_url" target="_blank">{{ sources.docs_url }}</a>
        </div>
        <!-- Loop through the GitHub repos -->
        <div v-for="repo in sources.github_repos" :key="repo" class="source-item">
          <span class="source-type">Repo:</span>
          <a :href="repo" target="_blank">{{ repo }}</a>
        </div>
      </div>
      
      <h2>Data Sources</h2>
      <div class="scrape-controls">
        <label for="scrape-limit">Messages to Scrape:</label>
        <input id="scrape-limit" type="number" v-model="scrapeLimit" />
      </div>
      <!-- This list is already dynamic, no changes needed here -->
      <ul>
        <li v-for="chat in chats" :key="chat.id" class="chat-item">
          <span class="chat-name">
            {{ chat.name }}
            <span class="message-count">({{ chat.message_count }})</span>
          </span>
          <button @click.stop="handleScrapeChat(chat.id)" :disabled="isScraping">
            {{ isScraping ? '...' : 'Scrape' }}
          </button>
        </li>
      </ul>
    </div>
    
    <div class="chat-window">
      <div class="chat-area">
    <div class="messages-container">
      <div v-for="(turn, index) in conversation" :key="index" :class="['turn', turn.role]">
        <div class="bubble">
          <pre>{{ turn.content }}</pre>
        </div>
      </div>
    </div>
    <div class="message-input">
      <input
        v-model="newMessage"
        @keyup.enter="handleSendMessage"
        :placeholder="isResponding ? 'AI is responding...' : 'Ask anything about the OpenIPC knowledge base...'"
        :disabled="isResponding"
      />
      <button @click="handleSendMessage" :disabled="isResponding">Send</button>
    </div>
  </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// MODIFIED: Import the new fetchSources function
import { fetchChats, scrapeChat, streamChat, fetchSources } from '../api';

// --- State Variables ---
const chats = ref([]);
const scrapeLimit = ref(100);
const isScraping = ref(false);
const conversation = ref([]);
const newMessage = ref('');
const isResponding = ref(false);

// NEW: A reactive object to hold our dynamic sources
const sources = ref({
  docs_url: '',
  github_repos: [],
  target_chats: []
});

// --- Lifecycle Hooks ---
onMounted(async () => {
  // Fetch both chats and sources when the component loads
  try {
    chats.value = await fetchChats();
    sources.value = await fetchSources();
  } catch (error) {
    console.error("Failed to load initial data:", error);
  }
  
  conversation.value = [
    { role: 'bot', content: 'Hello! I have knowledge of the OpenIPC GitHub repo, documentation, and scraped Telegram chats. Ask me anything.' }
  ];
});

// --- Methods ---
const handleScrapeChat = async (chatId) => {
  if (isScraping.value) return;
  isScraping.value = true;
  try {
    const result = await scrapeChat(chatId, scrapeLimit.value);
    if (result.status === 'success') {
      alert(`Scrape successful! ${result.messages_saved} new messages saved.`);
      chats.value = await fetchChats();
    } else {
      alert(`Could not scrape chat: ${result.detail || 'Unknown error'}`);
    }
  } catch (error) {
    alert('An error occurred during the scrape.');
  } finally {
    isScraping.value = false;
  }
};

const handleSendMessage = async () => {
  if (newMessage.value.trim() === '' || isResponding.value) return;
  const userQuery = newMessage.value;
  conversation.value.push({ role: 'user', content: userQuery });
  newMessage.value = '';
  isResponding.value = true;
  conversation.value.push({ role: 'bot', content: '' });
  const botMessageIndex = conversation.value.length - 1;
  try {
    await streamChat(userQuery, (chunk) => {
      conversation.value[botMessageIndex].content += chunk;
    });
  } catch (error) {
    console.error("Chat streaming error:", error);
    conversation.value[botMessageIndex].content = "Sorry, an error occurred.";
  } finally {
    isResponding.value = false;
  }
};
</script>

<style scoped>
  /* --- CORRECTED THEME BASED ON OpenIPC Companion --- */

  /* 1. Define variables INSIDE the component's top-level class */
  .chat-container {
    --background-main: #EAECEE;
    --background-sidebar: #2C3E50;
    --text-main: #34495E;
    --text-sidebar: #ECF0F1;
    --accent-blue: #3498DB;
    --accent-red: #E74C3C;
    --border-color: #3e566d; /* Darker border for the sidebar */
    --input-bg: #FFFFFF;
    --bot-bubble-bg: #FFFFFF;
    --bot-bubble-border: #dcdfe4;
    --hover-blue-bg: #3498DB;

    display: flex;
    height: 90vh;
    width: 80vw;
    overflow: hidden;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--background-main);
    color: var(--text-main);
  }

  /* 2. Sidebar / Data Sources Panel */
  .chat-list {
    width: 35%;
    flex-shrink: 0;
    background-color: var(--background-sidebar);
    color: var(--text-sidebar);
    border-right: 1px solid #1a2430;
    padding: 1rem;
    overflow-y: auto;
  }

  .chat-list h2 {
    margin-top: 0;
    font-weight: 600;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.75rem;
  }

  .scrape-controls {
    display: flex;
    align-items: center;
    gap: .5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
  }

  .scrape-controls label {
    font-size: .9em;
  }

  .scrape-controls input {
    width: 60px;
    padding: .25rem;
    background-color: #34495E;
    border: 1px solid var(--border-color);
    color: var(--text-sidebar);
    border-radius: 4px;
  }

  .chat-list ul {
    list-style-type: none;
    padding: 0;
    margin-top: 1rem;
  }

  .chat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: .75rem .5rem;
    cursor: default;
    border-bottom: 1px solid var(--border-color);
    transition: background-color 0.2s ease;
  }

  .chat-item:hover {
    background-color: var(--hover-blue-bg);
  }

  .chat-name {
    flex-grow: 1;
  }

  .message-count {
    color: #95a5a6;
    font-size: .8em;
    margin-left: .5rem;
  }

  .chat-item button {
    margin-left: 1rem;
    padding: .2rem .5rem;
    border: 1px solid var(--border-color);
    background-color: #34495E;
    color: var(--text-sidebar);
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .chat-item:hover button {
    background-color: var(--accent-blue);
    border-color: #fff;
  }
  
  .chat-item button:disabled {
    background-color: #2c3e50;
    border-color: #3e566d;
    color: #7f8c8d;
    cursor: not-allowed;
  }
  
  /* 3. Chat Window Panel */
  .chat-window {
    flex-grow: 1;
    display: flex;
    min-width: 0;
  }

  .chat-area {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    min-height: 0;
  }

  .messages-container {
    flex-grow: 1;
    overflow-y: auto;
    padding: 0 1rem;
  }

  .turn { display: flex; margin-bottom: 1rem; }
  .turn.user { justify-content: flex-end; }
  .turn.bot { justify-content: flex-start; }

  .bubble {
    max-width: 70%;
    padding: .75rem 1rem;
    border-radius: 1.25rem;
  }

  .turn.user .bubble {
    background-color: var(--accent-blue);
    color: white;
    border-bottom-right-radius: .25rem;
  }

  .turn.bot .bubble {
    background-color: var(--bot-bubble-bg);
    color: var(--text-main);
    border: 1px solid var(--bot-bubble-border);
    border-bottom-left-radius: .25rem;
  }

  .bubble pre {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: inherit;
    font-size: 1rem;
  }

  /* 4. Message Input Area */
  .message-input {
    display: flex;
    margin-top: 1rem;
    padding: 0.5rem;
    background: var(--input-bg);
    border-radius: 1.5rem;
    border: 1px solid #dcdfe4;
  }

  .message-input input {
    flex-grow: 1;
    padding: .75rem;
    border: none;
    background: transparent;
    outline: none;
    font-size: 1rem;
    color: var(--text-main);
  }
  
  .message-input input:disabled {
    color: #7f8c8d;
  }

  .message-input button {
    padding: .5rem 1.5rem;
    margin-left: .5rem;
    border-radius: 1.5rem;
    border: none;
    background-color: var(--accent-blue);
    color: white;
    cursor: pointer;
    font-weight: 600;
  }

  .message-input button:disabled {
    background-color: #95a5a6;
    cursor: not-allowed;
  }
</style>