(() => {
  const activity = document.getElementById('activity');
  const text = document.getElementById('activity-text');
  const elapsed = document.getElementById('activity-elapsed');
  const events = document.getElementById('activity-events');
  const toggle = document.getElementById('activity-toggle');

  const sanitize = value => {
    let s = String(value ?? '');
    // Normalize escaped HTML/tag variants sometimes emitted by reasoning models.
    s = s.replace(/\\?&lt;\s*(think|analysis|reasoning|internal)\s*&gt;/gi, '<$1>')
      .replace(/\\?&lt;\s*\/(think|analysis|reasoning|internal)\s*&gt;/gi, '</$1>')
      .replace(/\\?&lt;\|\s*(thinking|analysis|reasoning)\s*\|&gt;/gi, '<|$1|>')
      .replace(/\\?&lt;\|\s*end(?:thinking|analysis|reasoning)\s*\|&gt;/gi, '<|end$1|>');
    s = s.replace(/\\?\s*<think>[\s\S]*?<\/think>/gi, '')
      .replace(/\\?\s*<analysis>[\s\S]*?<\/analysis>/gi, '')
      .replace(/\\?\s*<reasoning>[\s\S]*?<\/reasoning>/gi, '')
      .replace(/\\?\s*<internal>[\s\S]*?<\/internal>/gi, '')
      .replace(/\\?\s*<\|(thinking|analysis|reasoning)\|>[\s\S]*?<\|end\1\|>/gi, '');
    // Defense in depth for an unterminated reasoning block.
    s = s.replace(/\\?\s*<(?:think|analysis|reasoning|internal)>[\s\S]*$/i, '')
      .replace(/\\?\s*<\|(?:thinking|analysis|reasoning)\|>[\s\S]*$/i, '');
    return s.trim();
  };

  // app.js already sanitizes before rendering. This second boundary sanitizes
  // the API response itself, including responses cached by older frontend code.
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    const request = args[0];
    const url = typeof request === 'string' ? request : request?.url || '';
    if (!url.includes('/api/v1/conversations/') || !url.endsWith('/messages')) return response;
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (data && typeof data === 'object') {
        ['answer', 'response', 'message', 'reply', 'content'].forEach(key => {
          if (typeof data[key] === 'string') data[key] = sanitize(data[key]);
        });
        return new Response(JSON.stringify(data), {
          status: response.status,
          statusText: response.statusText,
          headers: new Headers(response.headers)
        });
      }
    } catch (_) {
      // Preserve the original response if it is not JSON or cannot be cloned.
    }
    return response;
  };

  if (!activity || !text) return;

  const normalStages = [
    'Bitey está analizando tu solicitud…',
    'Bitey está organizando la información…',
    'Bitey está razonando sobre la mejor respuesta…',
    'Bitey está preparando una respuesta útil…'
  ];
  const attachmentStages = [
    'Bitey está revisando los archivos…',
    'Bitey está analizando el contenido…',
    'Bitey está relacionando la información…',
    'Bitey está preparando una respuesta útil…'
  ];

  let timer = null;
  let startedAt = 0;
  let index = 0;
  let lastVisible = false;

  const formatSeconds = ms => `${(ms / 1000).toFixed(1).replace('.', ',')} s`;
  const stop = () => { if (timer) clearInterval(timer); timer = null; };
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
    if (toggle) toggle.hidden = false;
  };

  window.BiteyThinking = { renderEvents };
  const start = () => {
    stop();
    startedAt = performance.now();
    index = 0;
    const hasAttachments = !!document.querySelector('.attachment-chip');
    const stages = hasAttachments ? attachmentStages : normalStages;
    text.textContent = stages[0];
    if (elapsed) elapsed.textContent = '0,0 s';
    resetEvents();
    timer = setInterval(() => {
      index = (index + 1) % stages.length;
      text.textContent = stages[index];
      if (elapsed) elapsed.textContent = formatSeconds(performance.now() - startedAt);
    }, 250);
  };
  const finish = ms => { stop(); if (elapsed) elapsed.textContent = formatSeconds(ms ?? (performance.now() - startedAt)); };
  const sync = () => {
    const visible = !activity.hidden;
    if (visible && !lastVisible) start();
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