const API_BASE = 'https://bitey-ia-suprabrain.onrender.com';
const API_PREFIX = '/api/v1';
const STORAGE_KEY = 'bitey_web_conversations_v1';

const messages = document.getElementById('messages');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const sendButton = document.getElementById('send');
const welcome = document.getElementById('welcome');
const newChat = document.getElementById('new-chat');
const history = document.getElementById('history');
const activity = document.getElementById('activity');
const activityText = document.getElementById('activity-text');
const clearLocal = document.getElementById('clear-local');
const mobileMenu = document.getElementById('mobile-menu');
const sidebar = document.querySelector('.sidebar');

const state = { conversationId: null, languagePreference: null, title: 'Nueva conversación' };

function loadLocalConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
  catch { return []; }
}

function saveLocalConversation() {
  if (!state.conversationId) return;
  const items = loadLocalConversations().filter(item => item.id !== state.conversationId);
  items.unshift({ id: state.conversationId, title: state.title, updatedAt: Date.now() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 30)));
  renderHistory();
}

function renderHistory() {
  if (!history) return;
  const items = loadLocalConversations();
  history.innerHTML = '';
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'history-empty';
    empty.textContent = 'Tus conversaciones aparecerán aquí.';
    history.appendChild(empty);
    return;
  }
  items.forEach(item => {
    const button = document.createElement('button');
    button.className = `history-item${item.id === state.conversationId ? ' active' : ''}`;
    button.textContent = item.title || 'Conversación';
    button.title = item.title || 'Conversación';
    button.addEventListener('click', () => openLocalConversation(item.id));
    history.appendChild(button);
  });
}

function openLocalConversation(id) {
  const item = loadLocalConversations().find(entry => entry.id === id);
  if (!item) return;
  state.conversationId = id;
  state.title = item.title;
  messages.innerHTML = '';
  const placeholder = document.createElement('div');
  placeholder.className = 'welcome compact-welcome';
  placeholder.innerHTML = '<div class="hero-mark">B</div><h1>Continuemos.</h1><p>La conversación está asociada al Supracerebro.</p>';
  messages.appendChild(placeholder);
  renderHistory();
  if (window.innerWidth < 760) sidebar.classList.remove('open');
  // The durable history is owned by the backend; this UI does not fabricate it.
}

function addMessage(role, text) {
  const currentWelcome = document.getElementById('welcome');
  if (currentWelcome) currentWelcome.remove();
  const row = document.createElement('div');
  row.className = `message ${role}`;
  if (role === 'assistant') {
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = 'B';
    row.appendChild(avatar);
  }
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

async function ensureConversation() {
  if (state.conversationId) return state.conversationId;
  const response = await fetch(`${API_BASE}${API_PREFIX}/conversations`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    body: JSON.stringify({ metadata: { channel: 'web', language: state.languagePreference, interface: 'bitey-web' } })
  });
  if (!response.ok) throw new Error(`Conversation HTTP ${response.status}`);
  const data = await response.json();
  state.conversationId = data.conversation_id;
  saveLocalConversation();
  return state.conversationId;
}

function setActivity(visible, text = 'Bitey está pensando…') {
  activity.hidden = !visible;
  activityText.textContent = text;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || sendButton.disabled) return;
  addMessage('user', message);
  promptInput.value = '';
  sendButton.disabled = true;
  setActivity(true, 'Bitey está procesando tu solicitud…');
  let pending = null;
  try {
    if (!state.title || state.title === 'Nueva conversación') {
      state.title = message.length > 42 ? `${message.slice(0, 42)}…` : message;
    }
    const conversationId = await ensureConversation();
    saveLocalConversation();
    pending = addMessage('assistant', '');
    pending.classList.add('typing');
    const response = await fetch(`${API_BASE}${API_PREFIX}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({ message, metadata: { channel: 'web', language: state.languagePreference, interface: 'bitey-web' } })
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail.slice(0, 300)}`);
    }
    const data = await response.json();
    pending.textContent = data.answer || 'No recibí una respuesta de Bitey.';
    pending.classList.remove('typing');
    saveLocalConversation();
  } catch (error) {
    if (pending) pending.textContent = 'No pude conectar con Bitey IA en este momento. Inténtalo nuevamente.';
    console.error('Bitey IA error:', error);
  } finally {
    setActivity(false);
    sendButton.disabled = false;
    promptInput.focus();
  }
}

function startNewChat() {
  state.conversationId = null;
  state.title = 'Nueva conversación';
  messages.innerHTML = `
    <div class="welcome" id="welcome">
      <div class="hero-mark">B</div><h1>Hola, soy Bitey.</h1>
      <p>Tu Supracerebro para investigar, resolver problemas y desarrollar ideas.</p>
      <div class="suggestions">
        <button data-prompt="Ayúdame a resolver un problema"><strong>Resolver</strong><span>Analiza un problema y encuentra una solución.</span></button>
        <button data-prompt="Quiero investigar una información en la web"><strong>Investigar</strong><span>Busca, contrasta y organiza información.</span></button>
        <button data-prompt="Quiero desarrollar una idea"><strong>Desarrollar</strong><span>Convierte una idea en un plan accionable.</span></button>
        <button data-prompt="Quiero crear una IA para mi empresa"><strong>IA para mi empresa</strong><span>Diseña una estrategia de IA adaptada al negocio.</span></button>
      </div>
    </div>`;
  bindSuggestions();
  renderHistory();
}

function bindSuggestions() {
  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.onclick = () => sendMessage(button.dataset.prompt);
  });
}

form.addEventListener('submit', event => { event.preventDefault(); sendMessage(promptInput.value); });
promptInput.addEventListener('input', () => {
  promptInput.style.height = 'auto';
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
});
promptInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
});
newChat.addEventListener('click', startNewChat);
clearLocal.addEventListener('click', () => {
  if (confirm('¿Limpiar el historial local de este navegador?')) {
    localStorage.removeItem(STORAGE_KEY);
    renderHistory();
  }
});
mobileMenu.addEventListener('click', () => sidebar.classList.toggle('open'));
bindSuggestions();
renderHistory();
