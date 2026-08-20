const API_BASE = 'https://bitefixes-backend.onrender.com';
const CHAT_PATH = '/chat';
const messages = document.getElementById('messages');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const sendButton = document.getElementById('send');
const welcome = document.getElementById('welcome');
const newChat = document.getElementById('new-chat');

const state = { conversationId: null, languagePreference: null };

function addMessage(role, text) {
  if (welcome) welcome.remove();
  const row = document.createElement('div');
  row.className = `message ${role}`;
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'assistant' ? 'B' : 'U';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  if (role === 'assistant') row.append(avatar, bubble); else row.append(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message) return;
  addMessage('user', message);
  promptInput.value = '';
  sendButton.disabled = true;
  const pending = addMessage('assistant', 'Bitey está pensando…');
  try {
    const body = {
      message,
      channel: 'web',
      conversation_id: state.conversationId,
      language_preference: state.languagePreference,
      history: []
    };
    const response = await fetch(`${API_BASE}${CHAT_PATH}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail.slice(0, 300)}`);
    }
    const data = await response.json();
    pending.textContent = data.response || data.message || 'No recibí una respuesta de Bitey.';
    state.conversationId = data.conversation_id ?? state.conversationId;
    state.languagePreference = data.language ?? data.language_preference ?? state.languagePreference;
  } catch (error) {
    pending.textContent = 'No pude conectar con Bitey Cloud en este momento. Inténtalo nuevamente.';
    console.error('Bitey Cloud error:', error);
  } finally {
    sendButton.disabled = false;
    promptInput.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage(promptInput.value);
});

promptInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

newChat.addEventListener('click', () => {
  state.conversationId = null;
  state.languagePreference = null;
  window.location.reload();
});

document.querySelectorAll('[data-prompt]').forEach(button => {
  button.addEventListener('click', () => sendMessage(button.dataset.prompt));
});
