<template>
  <div class="chat-container">
    <div class="chat-list">
      <h2>Chats</h2>
      <div class="scrape-controls">
        <label for="scrape-limit">Messages to Scrape:</label>
        <input id="scrape-limit" type="number" v-model="scrapeLimit" />
      </div>
      <ul>
        <li v-for="chat in chats" :key="chat.id" class="chat-item" @click="selectChat(chat.id)">
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
      <div v-if="selectedChatId" class="chat-area">
        <div class="messages-container">
          <!-- Loop through the new conversation turns -->
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
            :placeholder="isResponding ? 'AI is responding...' : 'Ask a question about this chat...'"
            :disabled="isResponding"
          />
          <button @click="handleSendMessage" :disabled="isResponding">Send</button>
        </div>
      </div>
      <div v-else class="no-chat-selected">
        <p>Select a chat to ask questions about it.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { fetchChats, scrapeChat, streamChat } from '../api';

const chats = ref([]);
const selectedChatId = ref(null);
const scrapeLimit = ref(100);
const isScraping = ref(false);

// NEW: State for the chatbot
const conversation = ref([]);
const newMessage = ref('');
const isResponding = ref(false);

onMounted(async () => {
  chats.value = await fetchChats();
});

const selectChat = (chatId) => {
  if (!chatId) return;
  selectedChatId.value = chatId;
  // Clear the conversation when switching chats
  conversation.value = [
    { role: 'bot', content: 'I am ready. Ask me anything about this chat\'s history.' }
  ];
};

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

const handleSendMessage = async () => {
  if (newMessage.value.trim() === '' || !selectedChatId.value || isResponding.value) return;

  const userQuery = newMessage.value;
  conversation.value.push({ role: 'user', content: userQuery });
  newMessage.value = ''; // Clear input immediately
  isResponding.value = true;

  // Add a placeholder for the bot's response
  conversation.value.push({ role: 'bot', content: '' });
  const botMessageIndex = conversation.value.length - 1;

  try {
    await streamChat(selectedChatId.value, userQuery, (chunk) => {
      // Append each received chunk to the bot's message content
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
/* ... (keep existing styles for chat-container, chat-list, etc.) ... */
.chat-container{display:flex;height:100vh}.chat-list{width:30%;border-right:1px solid #ccc;padding:1rem;overflow-y:auto}.scrape-controls{display:flex;align-items:center;gap:.5rem;padding-bottom:1rem;border-bottom:1px solid #eee}.scrape-controls label{font-size:.9em}.scrape-controls input{width:60px;padding:.25rem}.chat-list ul{list-style-type:none;padding:0;margin-top:1rem}.chat-item{display:flex;justify-content:space-between;align-items:center;padding:.5rem;cursor:pointer;border-bottom:1px solid #eee}.chat-item:hover{background-color:#f0f0f0}.chat-name{flex-grow:1}.message-count{color:#888;font-size:.8em;margin-left:.5rem}.chat-item button{margin-left:1rem;padding:.2rem .5rem;border:1px solid #ccc;border-radius:4px;cursor:pointer}.chat-item button:disabled{cursor:not-allowed;background-color:#eee}.no-chat-selected{display:flex;justify-content:center;align-items:center;height:100%;color:#888}

/* NEW & MODIFIED STYLES FOR CHATBOT UI */
.chat-window { width: 70%; display: flex; }
.chat-area { flex-grow: 1; display: flex; flex-direction: column; padding: 1rem; }
.messages-container { flex-grow: 1; overflow-y: auto; padding: 0 1rem; }
.turn { display: flex; margin-bottom: 1rem; }
.turn.user { justify-content: flex-end; }
.turn.bot { justify-content: flex-start; }
.bubble { max-width: 80%; padding: 0.75rem 1rem; border-radius: 1.25rem; }
.turn.user .bubble { background-color: #007aff; color: white; border-bottom-right-radius: 0.25rem; }
.turn.bot .bubble { background-color: #e5e5ea; color: black; border-bottom-left-radius: 0.25rem; }
.bubble pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 1rem; }
.message-input { display: flex; margin-top: 1rem; }
.message-input input { flex-grow: 1; padding: 0.75rem; border: 1px solid #ccc; border-radius: 1.5rem; }
.message-input input:disabled { background-color: #f5f5f5; }
.message-input button { padding: 0.5rem 1.5rem; margin-left: 0.5rem; border-radius: 1.5rem; }
</style>