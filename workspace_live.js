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
  async function getWorkspace(id){
    try{const r=await fetch(`${API()}/workspaces/${encodeURIComponent(id)}`);return r.ok?await r.json():null;}catch{return null;}
  }
  async function getWorkspaces(){
    try{const r=await fetch(`${API()}/workspaces`);return r.ok?(await r.json()).workspaces||[]:[];}catch{return [];}
  }
  function contextMarkup(data){
    const w=data?.workspace||{}; const memory=data?.memory||[]; const artifacts=data?.artifacts||[]; const tasks=data?.tasks||[];
    return `<div class="workspace-context-panel"><div class="feature-row"><span>◇</span><span><b>${esc(w.name||'Espacio de trabajo')}</b><small>${esc(w.description||'Contexto persistente de Bitey')}</small></span></div><div class="workspace-context-grid"><section><b>Memoria</b><small>${memory.length} elementos persistentes</small>${memory.slice(0,5).map(m=>`<div class="workspace-context-item"><strong>${esc(m.memory_type||'context')}</strong><span>${esc(m.content||'')}</span></div>`).join('')||'<small>No hay memoria registrada todavía.</small>'}</section><section><b>Resultados</b><small>${artifacts.length} artefactos persistidos</small>${artifacts.slice(0,5).map(a=>`<div class="workspace-context-item"><strong>${esc(a.artifact_type||'artefacto')}</strong><span>${esc(a.title||a.name||a.id||'Resultado')}</span></div>`).join('')||'<small>No hay artefactos todavía.</small>'}</section></div><div class="workspace-context-summary"><span>${tasks.length} tareas</span><span>${artifacts.length} resultados</span><span>${memory.length} recuerdos</span></div></div>`;
  }
  async function openContextPanel(){
    const modal=document.getElementById('modal-backdrop'), body=document.getElementById('modal-body'); if(!modal||!body)return;
    const ws=await getWorkspaces(); const current=ws[0];
    document.getElementById('modal-title').textContent='Proyectos y contexto';
    document.getElementById('modal-text').textContent='Bitey conserva el contexto de cada espacio y recupera sus resultados persistentes.';
    body.innerHTML=`<div class="workspace-context-select"><label for="bitey-context-workspace"><b>Espacio activo</b></label><select id="bitey-context-workspace">${ws.map(w=>`<option value="${esc(w.id)}">${esc(w.name||'Sin nombre')}</option>`).join('')||'<option value="">Sin espacios</option>'}</select></div><div id="bitey-context-content">${current?contextMarkup(await getWorkspace(current.id)):'<small>Crea un espacio desde Workspace para comenzar.</small>'}</div>`;
    const select=document.getElementById('bitey-context-workspace'); select?.addEventListener('change',async()=>{const data=await getWorkspace(select.value);document.getElementById('bitey-context-content').innerHTML=contextMarkup(data);});
    modal.classList.add('open');
  }
  window.BiteyLiveWorkspace={progress,start,stop,inspect,getWorkspace,getWorkspaces,openContextPanel};
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('[data-panel="projects"]').forEach(btn=>btn.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();openContextPanel();},true));
  });
})();
