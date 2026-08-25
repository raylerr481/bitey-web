(() => {
  const activity = document.getElementById('activity');
  const text = document.getElementById('activity-text');
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
  let index = 0;
  let lastVisible = false;

  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };

  const start = () => {
    stop();
    index = 0;
    const hasAttachments = !!document.querySelector('.attachment-chip');
    const stages = hasAttachments ? attachmentStages : normalStages;
    text.textContent = stages[0];
    timer = setInterval(() => {
      index = (index + 1) % stages.length;
      text.textContent = stages[index];
    }, 1700);
  };

  const sync = () => {
    const visible = !activity.hidden;
    if (visible && !lastVisible) start();
    if (!visible && lastVisible) stop();
    lastVisible = visible;
  };

  new MutationObserver(sync).observe(activity, { attributes: true, attributeFilter: ['hidden'] });
  sync();
})();
