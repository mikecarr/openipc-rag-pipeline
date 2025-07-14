<template>
  <div class="chat-container">
    <div class="chat-list">
      <h2>Data Sources</h2>
      <div class="scrape-controls">
        <label for="scrape-limit">Messages to Scrape:</label>
        <input id="scrape-limit" type="number" v-model="scrapeLimit" />
      </div>
      <ul>
        <!-- The list is now just for scraping -->
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
    
    <!-- MODIFIED: The chat window is now ALWAYS visible -->
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
// MODIFIED: We no longer need fetchMessages
import { fetchChats, scrapeChat, streamChat } from '../api';

const chats = ref([]);
const scrapeLimit = ref(100);
const isScraping = ref(false);

const conversation = ref([]);
const newMessage = ref('');
const isResponding = ref(false);

onMounted(async () => {
  // Set the initial state
  chats.value = await fetchChats();
  conversation.value = [
    { role: 'bot', content: 'Hello! I have knowledge of the OpenIPC GitHub repo, documentation, and scraped Telegram chats. Ask me anything.' }
  ];
});

const handleScrapeChat = async (chatId) => {
  if (isScraping.value) return;
  isScraping.value = true;
  try {
    const result = await scrapeChat(chatId, scrapeLimit.value);
    if (result.status === 'success') {
      alert(`Scrape successful! ${result.messages_saved} new messages saved.`);
      chats.value = await fetchChats(); // Refresh counts
    } else {
      alert(`Could not scrape chat: ${result.detail || 'Unknown error'}`);
    }
  } catch (error) {
    alert('An error occurred during the scrape.');
  } finally {
    isScraping.value = false;
  }
};

// MODIFIED: This function is now simpler
const handleSendMessage = async () => {
  if (newMessage.value.trim() === '' || isResponding.value) return;

  const userQuery = newMessage.value;
  conversation.value.push({ role: 'user', content: userQuery });
  newMessage.value = '';
  isResponding.value = true;

  conversation.value.push({ role: 'bot', content: '' });
  const botMessageIndex = conversation.value.length - 1;

  try {
    // We no longer pass a chatId
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
  .chat-container {
    display: flex;
    height: 90vh;
    width: 80vw;
    overflow: hidden; /* Prevent any potential overflow from the container itself */
  }

  .chat-list {
    width: 35%;
    flex-shrink: 0; /* Prevent the list from shrinking */
    border-right: 1px solid #ccc;
    padding: 1rem;
    overflow-y: auto;
    background-color: #f7f7f7;
  }

  .chat-list h2 {
    margin-top: 0;
  }

  .scrape-controls {
    display: flex;
    align-items: center;
    gap: .5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
  }

  .scrape-controls label {
    font-size: .9em;
  }

  .scrape-controls input {
    width: 60px;
    padding: .25rem;
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
    padding: .5rem;
    cursor: default;
    border-bottom: 1px solid #eee;
  }

  .chat-name {
    flex-grow: 1;
  }

  .chat-item button {
    margin-left: 1rem;
    padding: .2rem .5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    cursor: pointer;
  }

  .chat-item button:disabled {
    cursor: not-allowed;
    background-color: #eee;
  }

  .message-count {
    color: #888;
    font-size: .8em;
    margin-left: .5rem;
  }

  /* MODIFIED: This is a key change. Make chat-window a flex container that grows. */
  .chat-window {
    flex-grow: 1; /* This tells the window to fill all available horizontal space */
    display: flex;
    flex-direction: column; /* Stack its children vertically */
    /* This prevents the chat window from overflowing its parent */
    min-width: 0;
  }

  /* MODIFIED: The chat-area no longer needs its own flex properties */
  .chat-area {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    min-height: 0; /* Important for nested flexbox layouts */
  }
  
  .messages-container {
    flex-grow: 1;
    overflow-y: auto;
    padding: 0 1rem;
  }

  .turn {
    display: flex;
    margin-bottom: 1rem;
  }

  .turn.user {
    justify-content: flex-end;
  }

  .turn.bot {
    justify-content: flex-start;
  }

  .bubble {
    max-width: 80%;
    padding: .75rem 1rem;
    border-radius: 1.25rem;
  }

  .turn.user .bubble {
    background-color: #007aff;
    color: white;
    border-bottom-right-radius: .25rem;
  }

  .turn.bot .bubble {
    background-color: #e5e5ea;
    color: black;
    border-bottom-left-radius: .25rem;
  }

  .bubble pre {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: inherit;
    font-size: 1rem;
  }

  .message-input {
    display: flex;
    margin-top: 1rem;
    padding: 0.5rem;
    background: #f7f7f7;
    border-top: 1px solid #eee;
  }

  .message-input input {
    flex-grow: 1;
    padding: .75rem;
    border: 1px solid #ccc;
    border-radius: 1.5rem;
    outline: none;
  }
  
  .message-input input:disabled {
    background-color: #f0f0f0;
  }

  .message-input button {
    padding: .5rem 1.5rem;
    margin-left: .5rem;
    border-radius: 1.5rem;
    border: none;
    background-color: #007aff;
    color: white;
    cursor: pointer;
  }

  .message-input button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
</style>