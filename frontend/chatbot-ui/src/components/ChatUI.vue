<template>
  <div class="chat-container">
    <div class="chat-list">
      <h1>OpenIPC Chatbot</h1>
      <div class="knowledge-sources">
        <h2>Knowledge Sources</h2>
        <div v-for="url in sources.docs_urls" :key="url" class="source-item">
          <span class="source-type">Docs:</span>
          <a :href="url" target="_blank">{{ url }}</a>
        </div>
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

      <div class="admin-section">
        <button @click="openAdminPanel" class="stats-button">System Stats</button>
      </div>
    </div>

    <div class="chat-window">
      <div class="chat-area">
        <div class="messages-container">
          <!-- The v-for loop now renders the disclaimer correctly -->
          <div v-for="(turn, index) in conversation" :key="index" :class="['turn', turn.role]">
            <div class="bubble">
              <pre>{{ turn.content }}</pre>
              <!-- Disclaimer is now INSIDE the bubble -->
              <div v-if="turn.role === 'bot' && turn.finished" class="disclaimer">
                This information is AI-generated and may be inaccurate or contradictory.
              </div>
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

    <div v-if="showAdminPanel" class="admin-panel-overlay" @click="closeAdminPanel">
      <div class="admin-panel" @click.stop>
        <button class="close-button" @click="closeAdminPanel">×</button>
        <h2>System Statistics</h2>
        <div v-if="adminStats">
          <div class="stat-section">
            <h3>Knowledge Sources</h3>
            <div class="stat-item"><strong>Docs URLs:</strong>
              <ul><li v-for="url in adminStats.knowledge_sources.docs_urls" :key="url"><a :href="url" target="_blank">{{ url }}</a></li></ul>
            </div>
            <div class="stat-item"><strong>GitHub Repos:</strong>
              <ul><li v-for="repo in adminStats.knowledge_sources.github_repos" :key="repo"><a :href="repo" target="_blank">{{ repo }}</a></li></ul>
            </div>
          </div>
          <div class="stat-section">
            <h3>Vector Database (ChromaDB)</h3>
            <div class="stat-item"><strong>Location:</strong> <span>{{ adminStats.vector_database.location }}</span></div>
            <div class="stat-item"><strong>Total Vectors:</strong> <span>{{ adminStats.vector_database.total_vectors }}</span></div>
          </div>
          <div class="stat-section">
            <h3>Telegram Database (PostgreSQL)</h3>
            <div class="stat-item"><strong>Location:</strong> <span>{{ adminStats.telegram_database.location }}</span></div>
            <div class="stat-item"><strong>Total Messages Stored:</strong> <span>{{ adminStats.telegram_database.total_messages_stored }}</span></div>
            <h4>Per-Chat Details:</h4>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Chat ID</th>
                    <th>Message Count</th>
                    <th>Earliest Message</th>
                    <th>Latest Message</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="chat in adminStats.telegram_database.per_chat_statistics" :key="chat.chat_id">
                    <td>{{ chat.chat_id }}</td>
                    <td>{{ chat.message_count }}</td>
                    <td>{{ chat.earliest }}</td>
                    <td>{{ chat.latest }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div v-else>
          <p>Loading stats...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { fetchChats, scrapeChat, streamChat, fetchSources, fetchAdminStats } from '../api';

// --- State Variables ---
const chats = ref([]);
const scrapeLimit = ref(100);
const isScraping = ref(false);
const conversation = ref([]);
const newMessage = ref('');
const isResponding = ref(false);
const sources = ref({
  docs_urls: [],
  github_repos: [],
});
const showAdminPanel = ref(false);
const adminStats = ref(null);

// --- Lifecycle Hooks ---
onMounted(async () => {
  try {
    chats.value = await fetchChats();
    sources.value = await fetchSources();
  } catch (error) {
    console.error("Failed to load initial data:", error);
  }
  // MODIFIED: Added 'finished: true' to the initial bot message
  conversation.value = [
    { role: 'bot', content: 'Hello! I have knowledge of the OpenIPC GitHub repo, documentation, and scraped Telegram chats. Ask me anything.', finished: true }
  ];
});

// --- Methods ---
const openAdminPanel = async () => {
  showAdminPanel.value = true;
  adminStats.value = null;
  try {
    adminStats.value = await fetchAdminStats();
  } catch (error) {
    console.error("Failed to fetch admin stats:", error);
    alert("Could not load system stats.");
  }
};
const closeAdminPanel = () => {
  showAdminPanel.value = false;
};

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

// MODIFIED: The chat sending logic is updated to handle the disclaimer state
const handleSendMessage = async () => {
  if (newMessage.value.trim() === '' || isResponding.value) return;
  
  const userQuery = newMessage.value;
  conversation.value.push({ role: 'user', content: userQuery });
  newMessage.value = '';
  isResponding.value = true;

  // Add a placeholder for the bot's response with 'finished: false'
  conversation.value.push({ role: 'bot', content: '', finished: false });
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
    // Set 'finished: true' after the stream is complete
    if (conversation.value[botMessageIndex]) {
        conversation.value[botMessageIndex].finished = true;
    }
  }
};
</script>

<style scoped>
  /* --- FINAL, CORRECTED STYLES --- */

  .chat-container {
    --background-main: #EAECEE;
    --background-sidebar: #2C3E50;
    --text-main: #34495E;
    --text-sidebar: #ECF0F1;
    --accent-blue: #3498DB;
    --border-color: #3e566d;
    --input-bg: #FFFFFF;
    --bot-bubble-bg: #FFFFFF;
    --bot-bubble-border: #dcdfe4;
    --hover-blue-bg: #3498DB;

    display: flex;
    /* THIS IS THE LAYOUT FIX */
    height: 95vh;
    width: 85vw;
    overflow: hidden;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--background-main);
    color: var(--text-main);
  }

  /* All other styles are correct and included below */
  .chat-list{width:35%;flex-shrink:0;background-color:var(--background-sidebar);color:var(--text-sidebar);border-right:1px solid #1a2430;padding:1rem;overflow-y:auto}h1,h2{margin-top:0;font-weight:600;border-bottom:1px solid var(--border-color);padding-bottom:.75rem}.scrape-controls,.knowledge-sources{padding-bottom:1rem;margin-bottom:1rem;border-bottom:1px solid var(--border-color)}.scrape-controls label{font-size:.9em}.scrape-controls input{width:60px;padding:.25rem;background-color:#34495E;border:1px solid var(--border-color);color:var(--text-sidebar);border-radius:4px}.chat-list ul{list-style-type:none;padding:0;margin-top:1rem}.chat-item{display:flex;justify-content:space-between;align-items:center;padding:.75rem .5rem;cursor:default;border-bottom:1px solid var(--border-color);transition:background-color .2s ease}.chat-item:hover{background-color:var(--hover-blue-bg)}.chat-name{flex-grow:1}.message-count{color:#95a5a6;font-size:.8em;margin-left:.5rem}.chat-item button{margin-left:1rem;padding:.2rem .5rem;border:1px solid var(--border-color);background-color:#34495E;color:var(--text-sidebar);border-radius:4px;cursor:pointer;transition:background-color .2s ease}.chat-item:hover button{background-color:var(--accent-blue);border-color:#fff}.chat-item button:disabled{background-color:#2c3e50;border-color:#3e566d;color:#7f8c8d;cursor:not-allowed}.chat-window{flex-grow:1;display:flex;min-width:0}.chat-area{flex-grow:1;display:flex;flex-direction:column;padding:1rem;min-height:0}.messages-container{flex-grow:1;overflow-y:auto;padding:0 1rem}.turn{display:flex;flex-direction:column;margin-bottom:1rem}.turn.user{align-items:flex-end}.turn.bot{align-items:flex-start}.bubble{max-width:80%;padding:.75rem 1rem;border-radius:1.25rem}.turn.user .bubble{background-color:var(--accent-blue);color:white;border-bottom-right-radius:.25rem}.turn.bot .bubble{background-color:var(--bot-bubble-bg);color:var(--text-main);border:1px solid var(--bot-bubble-border);border-bottom-left-radius:.25rem}.bubble pre{margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:inherit;font-size:1rem}
  
  /* THIS IS THE DISCLAIMER FIX */
  .disclaimer{font-size:.7rem;color:#7f8c8d;font-style:italic;border-top:1px solid #e0e0e0;padding-top:.5rem;margin-top:.75rem}
  
  .message-input{display:flex;margin-top:1rem;padding:.5rem;background:var(--input-bg);border-radius:1.5rem;border:1px solid #dcdfe4}.message-input input{flex-grow:1;padding:.75rem;border:none;background:transparent;outline:none;font-size:1rem;color:var(--text-main)}.message-input input:disabled{color:#7f8c8d}.message-input button{padding:.5rem 1.5rem;margin-left:.5rem;border-radius:1.5rem;border:none;background-color:var(--accent-blue);color:white;cursor:pointer;font-weight:600}.message-input button:disabled{background-color:#95a5a6;cursor:not-allowed}.admin-section{margin-top:2rem;padding-top:1rem;border-top:1px solid var(--border-color)}.stats-button{width:100%;padding:.75rem;background-color:#34495E;color:white;border:1px solid var(--border-color);border-radius:4px;cursor:pointer;font-size:1rem;font-weight:600;transition:background-color .2s ease}.stats-button:hover{background-color:var(--hover-blue-bg)}.admin-panel-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background-color:rgba(0,0,0,.6);display:flex;justify-content:center;align-items:center;z-index:1000;backdrop-filter:blur(5px)}.admin-panel{background-color:#fcfcfc;padding:2rem;border-radius:12px;width:90%;max-width:950px;max-height:90vh;overflow-y:auto;position:relative;color:var(--text-main);box-shadow:0 10px 30px rgba(0,0,0,.2)}.admin-panel h2{text-align:center;margin-top:0;margin-bottom:2rem;font-size:1.75rem;color:#2c3e50}.admin-panel h3{font-size:1.25rem;color:#2c3e50;border-bottom:2px solid var(--accent-blue);padding-bottom:.5rem;margin-bottom:1.5rem}.close-button{position:absolute;top:15px;right:20px;background:none;border:none;font-size:2.5rem;line-height:1;cursor:pointer;color:#bdc3c7;transition:color .2s ease}.close-button:hover{color:#7f8c8d}.stat-section{margin-bottom:2.5rem}.stat-item{margin-bottom:.75rem;font-size:1rem;display:flex;align-items:flex-start}.stat-item strong{display:inline-block;width:180px;flex-shrink:0;color:#2c3e50}.stat-item span,.stat-item a{color:#555}.stat-item a{color:var(--accent-blue);text-decoration:none}.stat-item a:hover{text-decoration:underline}.stat-item ul{list-style:none;padding-left:0;margin:0}.stat-item ul li{margin-bottom:.25rem}h4{margin-top:2rem;margin-bottom:1rem;color:#2c3e50}.table-container{width:100%;overflow-x:auto;border:1px solid #ddd;border-radius:8px}table{width:100%;border-collapse:collapse}th,td{padding:12px 15px;text-align:left;border-bottom:1px solid #ddd}thead tr{background-color:#f2f7fa}th{font-weight:600;color:#2c3e50}tbody tr:last-child td{border-bottom:none}tbody tr:nth-of-type(even){background-color:#f9f9f9}.knowledge-sources .source-item{display:flex;align-items:flex-start;padding:.25rem 0;font-size:.9em}.source-type{font-weight:600;width:50px;flex-shrink:0}.knowledge-sources a{color:var(--text-sidebar);text-decoration:none;word-break:break-all}.knowledge-sources a:hover{text-decoration:underline;color:var(--accent-blue)}
</style>