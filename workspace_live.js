(() => {
  'use strict';
  const API = () => `${window.BITEY_API_BASE || ''}/api/v1`;
  const state = { timer: null, started: 0 };
  const phases = ['Pensando','Planificando','Investigando','Generando','Evaluando','Listo'];
  const esc = v => String(v ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const phaseIndex = p => ({planning:1,researching:2,generating:3,evaluating:4,completed:5,ready:5}[p] ?? 1);
  function progress(plan, phase='planning') {
    const active = phaseIndex(phase);
    return `<div class="live-cognitive"><div class="live-head"><span class="live-pulse"></span><div><b>Bitey está trabajando</b><small>${esc(plan?.route === 'research' ? 'Investigación acotada' : plan?.route === 'artifact' ? 'Creación de resultado' : 'Razonamiento y ejecución')}</small></div><span class="live-time" data-live-time>0,0 s</span></div><div class="live-phases">${phases.map((x,i)=>`<span class="${i<active?'done ':''}${i===active?'active':''}">${i<active?'✓ ':''}${x}</span>`).join('')}</div></div>`;
  }
  function start(el){
    if (!el) return;
    state.started = performance.now();
    clearInterval(state.timer);
    const tick=()=>{ const node=el.querySelector('[data-live-time]'); if(node)node.textContent=((performance.now()-state.started)/1000).toFixed(1).replace('.',',')+' s'; };
    tick(); state.timer=setInterval(tick,100);
  }
  function stop(){clearInterval(state.timer);state.timer=null;}
  async function inspect(prompt, capability='chat', context={}){
    try{const r=await fetch(`${API()}/workspace/cognitive/inspect`,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({prompt,capability,context})});return r.ok?await r.json():null;}catch{return null;}
  }
  window.BiteyLiveWorkspace={progress,start,stop,inspect};
})();
