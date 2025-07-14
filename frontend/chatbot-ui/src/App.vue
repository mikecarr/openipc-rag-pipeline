<!-- frontend/chatbot-ui/src/App.vue -->
<template>
  <main>
    <!-- This line tells Vue to load and display our real chat component -->
    <ChatUI />
  </main>
</template>

<script setup>
// We import the component so we can use it in the template
import ChatUI from './components/ChatUI.vue'
</script>

<style>
/* Basic global styles */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

main {
  height: 100vh;
  width: 100vw;
}
</style>