const API_BASE = 'https://bitey-ia-suprabrain.onrender.com';
const API_PREFIX = '/api/v1';
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

async function ensureConversation() {
  if (state.conversationId) return state.conversationId;
  const response = await fetch(`${API_BASE}${API_PREFIX}/conversations`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    body: JSON.stringify({ metadata: { channel: 'web', language: state.languagePreference } })
  });
  if (!response.ok) throw new Error(`Conversation HTTP ${response.status}`);
  const data = await response.json();
  state.conversationId = data.conversation_id;
  return state.conversationId;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message) return;
  addMessage('user', message);
  promptInput.value = '';
  sendButton.disabled = true;
  const pending = addMessage('assistant', 'Bitey está pensando…');
  try {
    const conversationId = await ensureConversation();
    const response = await fetch(`${API_BASE}${API_PREFIX}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({
        message,
        metadata: {
          channel: 'web',
          language: state.languagePreference,
          interface: 'bitey-web'
        }
      })
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail.slice(0, 300)}`);
    }
    const data = await response.json();
    pending.textContent = data.answer || 'No recibí una respuesta de Bitey.';
  } catch (error) {
    pending.textContent = 'No pude conectar con Bitey IA en este momento. Inténtalo nuevamente.';
    console.error('Bitey IA error:', error);
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
