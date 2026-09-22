(() => {
  const activity = document.getElementById('activity');
  const text = document.getElementById('activity-text');
  const elapsed = document.getElementById('activity-elapsed');
  const events = document.getElementById('activity-events');
  const toggle = document.getElementById('activity-toggle');

  const sanitize = value => {
    let s = String(value ?? '');
    s = s.replace(/\\?&lt;\s*(think|analysis|reasoning|internal)\s*&gt;/gi, '<$1>')
      .replace(/\\?&lt;\s*\/(think|analysis|reasoning|internal)\s*&gt;/gi, '</$1>')
      .replace(/\\?&lt;\|\s*(thinking|analysis|reasoning)\s*\|&gt;/gi, '<|$1|>')
      .replace(/\\?&lt;\|\s*end(?:thinking|analysis|reasoning)\s*\|&gt;/gi, '<|end$1|>');
    s = s.replace(/\\?\s*<think>[\s\S]*?<\/think>/gi, '')
      .replace(/\\?\s*<analysis>[\s\S]*?<\/analysis>/gi, '')
      .replace(/\\?\s*<reasoning>[\s\S]*?<\/reasoning>/gi, '')
      .replace(/\\?\s*<internal>[\s\S]*?<\/internal>/gi, '')
      .replace(/\\?\s*<\|(thinking|analysis|reasoning)\|>[\s\S]*?<\|end\1\|>/gi, '');
    s = s.replace(/\\?\s*<(?:think|analysis|reasoning|internal)>[\s\S]*$/i, '')
      .replace(/\\?\s*<\|(?:thinking|analysis|reasoning)\|>[\s\S]*$/i, '');

    const prose = /(?:here(?:'s| is)\s+(?:a\s+)?thinking\s+process|thinking\s+process|chain\s+of\s+thought|proceso\s+de\s+pensamiento|razonamiento\s+interno|analyze\s+user\s+input|identify\s+(?:core\s+)?(?:question|topic|requirements)|retrieve\s+knowledge|formulate\s+response|check\s+constraints|refine\s+response)/i;
    const finalMarker = /(?:^|\n)\s*(?:final\s+answer|respuesta\s+final|respuesta|draft(?:\s*\(\s*mental\s*\))?)\s*:\s*/i;
    if (prose.test(s)) {
      const marker = s.match(finalMarker);
      const draft = s.match(/(?:^|\n)\s*draft(?:\s*\(\s*mental\s*\))?\s*:\s*(.+)$/is);
      if (marker) s = s.slice(marker.index + marker[0].length);
      else if (draft) s = draft[1];
      else return '';
    }
    if (/^\s*No puedo mostrar el razonamiento interno/i.test(s)) return '';
    return s.replace(/\n{3,}/g, '\n\n').trim();
  };

  // Second public-output boundary: sanitize both new API responses and
  // responses loaded from conversation history.
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    const request = args[0];
    const url = typeof request === 'string' ? request : request?.url || '';
    const isMessagePost = /\/api\/v1\/conversations\/[^/]+\/messages$/.test(url) && String(args[1]?.method || 'GET').toUpperCase() === 'POST';
    if (isMessagePost) {
      try {
        const match = url.match(/\/api\/v1\/conversations\/([^/]+)\/messages$/);
        const conversationId = decodeURIComponent(match?.[1] || '');
        const body = typeof args[1]?.body === 'string' ? JSON.parse(args[1].body) : null;
        const requestId = body?.metadata?.request_id || null;
        if (conversationId) startLive(conversationId, requestId);
      } catch (_) {}
      return response;
    }
    if (!url.includes('/api/v1/conversations/') || !url.endsWith('/messages')) return response;
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (data && typeof data === 'object') {
        ['answer', 'response', 'message', 'reply', 'content'].forEach(key => {
          if (typeof data[key] === 'string') data[key] = sanitize(data[key]);
        });
        if (Array.isArray(data.messages)) data.messages = data.messages.map(item => {
          if (item && typeof item.content === 'string') item.content = sanitize(item.content);
          return item;
        });
        return new Response(JSON.stringify(data), {
          status: response.status,
          statusText: response.statusText,
          headers: new Headers(response.headers)
        });
      }
    } catch (_) {}
    return response;
  };

  if (!activity || !text) return;

  const normalLabel = 'Bitey está analizando tu solicitud…';
  let pollTimer = null;
  let liveRequestId = null;
  let liveConversationId = null;
  let lastVisible = false;

  const resetEvents = () => {
    if (!events) return;
    events.innerHTML = '';
    events.hidden = true;
    if (toggle) {
      toggle.hidden = true;
      toggle.textContent = 'Ver actividad';
      toggle.setAttribute('aria-expanded', 'false');
    }
  };

  const stopPolling = () => {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    liveRequestId = null;
    liveConversationId = null;
  };

  const renderEvents = list => {
    if (!events || !Array.isArray(list) || !list.length) return;
    events.innerHTML = '';
    list.forEach((item, i) => {
      const row = document.createElement('div');
      row.className = 'activity-event';
      const check = document.createElement('span');
      check.className = 'activity-check';
      check.textContent = i === list.length - 1 ? '•' : '✓';
      const label = document.createElement('span');
      label.textContent = sanitize(item);
      row.append(check, label);
      events.appendChild(row);
    });
    events.hidden = false;
    if (toggle) {
      toggle.hidden = false;
      toggle.textContent = 'Ver actividad';
      toggle.setAttribute('aria-expanded', 'false');
    }
  };

  const renderLiveTrace = trace => {
    if (!trace) return;
    const list = Array.isArray(trace.activities) ? trace.activities : [];
    if (list.length) renderEvents(list);
    const last = list[list.length - 1];
    if (last && text) text.textContent = sanitize(last);
    if (elapsed && trace.created_at) {
      elapsed.textContent = `${Math.max(0, (Date.now() - new Date(trace.created_at).getTime()) / 1000).toFixed(1).replace('.', ',')} s`;
    }
  };

  const pollTrace = async () => {
    if (!liveConversationId) return;
    try {
      const base = window.BITEY_API_BASE || 'https://bitey-ia-suprabrain.onrender.com';
      const requestFilter = liveRequestId ? `&request_id=${encodeURIComponent(liveRequestId)}` : '';
      const url = `${base}/api/v1/cognitive/traces?conversation_id=${encodeURIComponent(liveConversationId)}${requestFilter}&limit=1`;
      const response = await nativeFetch(url, { headers: { 'Accept': 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      const trace = data?.traces?.[0];
      if (!trace) return;
      renderLiveTrace(trace);
      if (trace.final_status && trace.final_status !== 'running') stopPolling();
    } catch (_) {}
  };

  const startLive = (conversationId, requestId) => {
    stopPolling();
    if (!conversationId || !requestId) return;
    liveConversationId = conversationId;
    liveRequestId = requestId;
    if (text) text.textContent = normalLabel;
    resetEvents();
    pollTrace();
    pollTimer = setInterval(pollTrace, 350);
  };

  const finish = () => stopPolling();

  window.BiteyThinking = { renderEvents, startLive, finish };

  const sync = () => {
    const visible = !activity.hidden;
    if (visible && !lastVisible && text) text.textContent = normalLabel;
    if (!visible && lastVisible) finish();
    lastVisible = visible;
  };

  toggle?.addEventListener('click', () => {
    const open = !!events?.hidden;
    if (events) events.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.textContent = open ? 'Ocultar actividad' : 'Ver actividad';
  });

  new MutationObserver(sync).observe(activity, { attributes: true, attributeFilter: ['hidden'] });
  sync();
})();