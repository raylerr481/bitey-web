(() => {
  const activity = document.getElementById('activity');
  const text = document.getElementById('activity-text');
  const elapsed = document.getElementById('activity-elapsed');
  const events = document.getElementById('activity-events');
  const toggle = document.getElementById('activity-toggle');
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

  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };

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
      row.innerHTML = `<span class="activity-check">${i === list.length - 1 ? '•' : '✓'}</span><span>${String(item)}</span>`;
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

  const finish = ms => {
    stop();
    if (elapsed) elapsed.textContent = formatSeconds(ms ?? (performance.now() - startedAt));
  };

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
