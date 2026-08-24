const API_BASE = window.BITEY_API_BASE || '';
const API_PREFIX = '/api/v1';
const STORAGE_KEY = 'bitey_web_conversations_v1';

const messages = document.getElementById('messages');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const sendButton = document.getElementById('send');
const newChat = document.getElementById('new-chat');
const history = document.getElementById('history');
const activity = document.getElementById('activity');
const activityText = document.getElementById('activity-text');
const clearLocal = document.getElementById('clear-local');
const mobileMenu = document.getElementById('mobile-menu');
const sidebar = document.querySelector('.sidebar');
const searchChats = document.getElementById('search-chats');
const searchPanel = document.getElementById('search-panel');
const historySearch = document.getElementById('history-search');
const modalBackdrop = document.getElementById('modal-backdrop');
const modalTitle = document.getElementById('modal-title');
const modalText = document.getElementById('modal-text');
const modalClose = document.getElementById('modal-close');
const attachButton = document.getElementById('attach-button');
const attachMenu = document.getElementById('attach-menu');
const fileInput = document.getElementById('file-input');
const attachmentPreview = document.getElementById('attachment-preview');
const voiceButton = document.getElementById('voice-button');

const state = { conversationId: null, languagePreference: null, title: 'Nueva conversación', attachments: [], listening: false };

function loadLocalConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
  catch { return []; }
}

function saveLocalConversation() {
  if (!state.conversationId) return;
  const items = loadLocalConversations().filter(item => item.id !== state.conversationId);
  items.unshift({ id: state.conversationId, title: state.title, updatedAt: Date.now() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
  renderHistory();
}

function renderHistory(filter = '') {
  if (!history) return;
  const query = filter.trim().toLowerCase();
  const items = loadLocalConversations().filter(item => !query || (item.title || '').toLowerCase().includes(query));
  history.innerHTML = '';
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'history-empty';
    empty.textContent = query ? 'No se encontraron conversaciones.' : 'Tus conversaciones aparecerán aquí.';
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
  placeholder.innerHTML = '<div class="hero-mark">B</div><h1>Continuemos.</h1><p>Esta conversación está asociada al Supracerebro.</p>';
  messages.appendChild(placeholder);
  renderHistory(historySearch ? historySearch.value : '');
  if (window.innerWidth < 760) sidebar.classList.remove('open');
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
  if (!activity) return;
  activity.hidden = !visible;
  if (activityText) activityText.textContent = text;
}

function renderAttachments() {
  if (!attachmentPreview) return;
  attachmentPreview.innerHTML = '';
  state.attachments.forEach((file, index) => {
    const chip = document.createElement('div');
    chip.className = 'attachment-chip';
    const icon = file.type.startsWith('image/') ? '🖼️' : '📎';
    chip.innerHTML = `<span>${icon}</span><span class="attachment-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span><button type="button" aria-label="Quitar ${escapeHtml(file.name)}" data-remove-attachment="${index}">×</button>`;
    attachmentPreview.appendChild(chip);
  });
  attachmentPreview.querySelectorAll('[data-remove-attachment]').forEach(button => {
    button.addEventListener('click', () => {
      state.attachments.splice(Number(button.dataset.removeAttachment), 1);
      renderAttachments();
    });
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function acceptFor(kind) {
  if (kind === 'image') return 'image/*';
  if (kind === 'data') return '.csv,.xlsx,.xls,.json,.jsonl,.tsv';
  return '.pdf,.doc,.docx,.txt,.md,.rtf,.csv,.xlsx,.xls,.json,.jsonl,.tsv,.png,.jpg,.jpeg,.webp';
}

function chooseAttachment(kind) {
  if (kind === 'library') {
    showModal('Biblioteca', 'La Biblioteca de Bitey está preparada para conectarse al almacenamiento persistente. Aquí podrás seleccionar archivos guardados sin salir de la conversación.');
    closeAttachMenu();
    return;
  }
  fileInput.accept = acceptFor(kind);
  fileInput.dataset.kind = kind;
  fileInput.click();
  closeAttachMenu();
}

function closeAttachMenu() {
  if (!attachMenu) return;
  attachMenu.classList.remove('open');
  attachButton?.setAttribute('aria-expanded', 'false');
}

function toggleAttachMenu() {
  const open = attachMenu.classList.toggle('open');
  attachButton?.setAttribute('aria-expanded', String(open));
}

async function sendMessage(text) {
  const message = text.trim();
  if ((!message && !state.attachments.length) || sendButton.disabled) return;
  const attachmentNames = state.attachments.map(file => file.name);
  const visibleMessage = message || `Archivos adjuntos: ${attachmentNames.join(', ')}`;
  addMessage('user', visibleMessage);
  promptInput.value = '';
  promptInput.style.height = 'auto';
  sendButton.disabled = true;
  setActivity(true, state.attachments.length ? 'Bitey está preparando tu solicitud…' : 'Bitey está procesando tu solicitud…');
  let pending = null;
  try {
    if (!state.title || state.title === 'Nueva conversación') {
      state.title = message ? (message.length > 50 ? `${message.slice(0, 50)}…` : message) : attachmentNames[0] || 'Archivos';
    }
    const conversationId = await ensureConversation();
    saveLocalConversation();
    pending = addMessage('assistant', '');
    pending.classList.add('typing');
    const response = await fetch(`${API_BASE}${API_PREFIX}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({ message: message || visibleMessage, metadata: { channel: 'web', language: state.languagePreference, interface: 'bitey-web', attachments: attachmentNames } })
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail.slice(0, 300)}`);
    }
    const data = await response.json();
    pending.textContent = data.answer || 'No recibí una respuesta de Bitey.';
    pending.classList.remove('typing');
    saveLocalConversation();
    state.attachments = [];
    renderAttachments();
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
  state.attachments = [];
  renderAttachments();
  messages.innerHTML = '<div class="welcome" id="welcome"><div class="hero-mark">B</div><div class="eyebrow">Bitey IA</div><h1>Hola, soy Bitey.</h1><p class="hero-copy">¿En qué estás pensando?</p></div>';
  renderHistory();
  promptInput.focus();
  if (window.innerWidth < 760) sidebar.classList.remove('open');
}

function showModal(title, text) {
  modalTitle.textContent = title;
  modalText.textContent = text;
  modalBackdrop.classList.add('open');
}

function closeModal() { modalBackdrop.classList.remove('open'); }

form.addEventListener('submit', event => { event.preventDefault(); sendMessage(promptInput.value); });
promptInput.addEventListener('input', () => {
  promptInput.style.height = 'auto';
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
});
promptInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
});
newChat.addEventListener('click', startNewChat);

attachButton?.addEventListener('click', toggleAttachMenu);
document.querySelectorAll('[data-attach]').forEach(button => button.addEventListener('click', () => chooseAttachment(button.dataset.attach)));
fileInput?.addEventListener('change', event => {
  const files = Array.from(event.target.files || []);
  state.attachments.push(...files);
  renderAttachments();
  event.target.value = '';
});
document.addEventListener('click', event => {
  if (attachMenu?.classList.contains('open') && !event.target.closest('.composer')) closeAttachMenu();
});

function setupVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceButton?.addEventListener('click', () => showModal('Voz', 'La entrada por voz no está disponible en este navegador. Usa un navegador compatible con Speech Recognition.'));
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = navigator.language || 'es-ES';
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.onstart = () => { state.listening = true; voiceButton.classList.add('recording'); voiceButton.setAttribute('aria-label', 'Detener micrófono'); };
  recognition.onresult = event => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) transcript += event.results[i][0].transcript;
    promptInput.value = transcript;
    promptInput.dispatchEvent(new Event('input'));
  };
  recognition.onerror = event => console.warn('Bitey voice error:', event.error);
  recognition.onend = () => { state.listening = false; voiceButton.classList.remove('recording'); voiceButton.setAttribute('aria-label', 'Usar micrófono'); promptInput.focus(); };
  voiceButton?.addEventListener('click', () => {
    if (state.listening) recognition.stop();
    else { recognition.lang = navigator.language || 'es-ES'; recognition.start(); }
  });
}
setupVoice();

if (clearLocal) clearLocal.addEventListener('click', () => {
  showModal('Opciones de conversación', 'Puedes limpiar el historial local de este navegador. El historial almacenado en el Supracerebro no se elimina desde aquí.');
});
if (searchChats) searchChats.addEventListener('click', () => {
  searchPanel.classList.toggle('open');
  if (searchPanel.classList.contains('open')) historySearch.focus();
});
if (historySearch) historySearch.addEventListener('input', () => renderHistory(historySearch.value));
if (mobileMenu) mobileMenu.addEventListener('click', () => sidebar.classList.toggle('open'));
if (modalClose) modalClose.addEventListener('click', closeModal);
if (modalBackdrop) modalBackdrop.addEventListener('click', event => { if (event.target === modalBackdrop) closeModal(); });

document.querySelectorAll('[data-panel]').forEach(button => {
  button.addEventListener('click', () => {
    const labels = { library: 'Biblioteca', projects: 'Proyectos', explore: 'Explorar IA' };
    showModal(labels[button.dataset.panel] || 'Bitey IA', 'Esta capacidad forma parte de la interfaz del Supracerebro y será conectada progresivamente al backend.');
  });
});

document.getElementById('settings')?.addEventListener('click', () => showModal('Configuración', 'Aquí se centralizarán las preferencias de Bitey IA, memoria, privacidad, idioma, apariencia y proveedores.'));
document.getElementById('help')?.addEventListener('click', () => showModal('Ayuda', 'Bitey IA es el Supracerebro. Escribe tu solicitud en el cuadro de texto para iniciar una conversación.'));
document.getElementById('profile')?.addEventListener('click', () => showModal('Bitey IA', 'Supracerebro independiente de BiteFixes Backend.'));

renderHistory();
renderAttachments();
promptInput.focus();
