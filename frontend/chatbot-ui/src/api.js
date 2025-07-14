const API_BASE = "http://localhost:8000"; // or docker network alias like "http://telegram-bot:8000"

export async function fetchChats() {
  const res = await fetch(`${API_BASE}/chats`);
  return await res.json();
}

export async function fetchMessages(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}/messages`);
  return await res.json();
}

export async function sendMessage(chatId, text) {
  const res = await fetch(`${API_BASE}/chats/${chatId}/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return await res.json();
}

export async function scrapeChat(chatId, limit = 100) {
  // Add the limit as a query parameter to the URL
  const res = await fetch(`${API_BASE}/chats/${chatId}/scrape?limit=${limit}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Scraping failed with status: ${res.status}`);
  }
  return await res.json();
}

export async function fetchSummary(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch summary: ${res.status}`);
  }
  return await res.json();
}

// In src/api.js

export async function streamChat(chatId, query, onChunk) {
  const res = await fetch(`${API_BASE}/chats/${chatId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!res.ok) {
    throw new Error(`Chat API failed with status: ${res.status}`);
  }
  
  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    const chunk = decoder.decode(value);
    onChunk(chunk); // Call the callback with the new text chunk
  }
}