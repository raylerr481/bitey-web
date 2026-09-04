(() => {
  const API = () => `${window.BITEY_API_BASE || ''}/api/v1`;
  const esc = s => String(s ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const modal = () => document.getElementById('modal-backdrop');
  const body = () => document.getElementById('modal-body');
  const open = (title, text, html='') => { const m=modal(); if(!m)return; document.getElementById('modal-title').textContent=title; document.getElementById('modal-text').textContent=text; body().innerHTML=html; m.classList.add('open'); };
  const close = () => modal()?.classList.remove('open');
  async function catalog(){ try{ const r=await fetch(`${API()}/workspace/catalog`); return r.ok?await r.json():null; }catch{return null;} }
  async function workspaces(){ try{ const r=await fetch(`${API()}/workspaces`); return r.ok?(await r.json()).workspaces||[]:[]; }catch{return [];} }
  async function createWorkspace(name){ const r=await fetch(`${API()}/workspaces`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); return r.ok?r.json():null; }
  async function createTask(id, capability, prompt){ const r=await fetch(`${API()}/workspaces/${encodeURIComponent(id)}/tasks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:prompt.slice(0,80)||'Nueva tarea',prompt,capability})}); return r.ok?r.json():null; }
  async function hub(){
    const [c, ws] = await Promise.all([catalog(), workspaces()]);
    const caps = c?.capabilities || [
      {id:'chat',label:'Chat',kind:'conversation'},{id:'deep_research',label:'Investigación profunda',kind:'research'},
      {id:'documents',label:'Documentos',kind:'artifact'},{id:'slides',label:'Presentaciones',kind:'artifact'},
      {id:'spreadsheets',label:'Hojas de cálculo',kind:'artifact'},{id:'code',label:'Código',kind:'artifact'},
      {id:'files',label:'Archivos',kind:'context'},{id:'agents',label:'Agentes',kind:'orchestration'}
    ];
    const current = ws[0];
    open('Workspace de Bitey IA','Un espacio de trabajo integral para investigar, crear y ejecutar tareas con el cerebro cognitivo de Bitey.',
      `<div class="workspace-grid">${caps.map(x=>`<button class="workspace-card" data-cap="${esc(x.id)}"><span class="workspace-icon">${x.id==='deep_research'?'✦':x.id==='documents'?'▤':x.id==='slides'?'▥':x.id==='spreadsheets'?'▦':x.id==='code'?'⌘':x.id==='files'?'▣':x.id==='agents'?'◈':'◌'}</span><b>${esc(x.label)}</b><small>${esc(x.kind)}</small></button>`).join('')}</div><div class="workspace-list"><div class="feature-row"><span>◇</span><span><b>${esc(current?.name || 'Espacio general')}</b><small>${ws.length ? `${ws.length} espacios disponibles` : 'Crea tu primer espacio de trabajo'}</small></span></div><button class="primary-action" id="new-workspace">＋ Nuevo espacio</button></div>`);
    body()?.querySelectorAll('[data-cap]').forEach(b=>b.onclick=async()=>{
      const capability=b.dataset.cap, prompt=window.prompt(`¿Qué quieres hacer con ${b.textContent.trim()}?`);
      if(!prompt?.trim()) return;
      let w=current; if(!w) w=await createWorkspace('Espacio general');
      if(w) await createTask(w.id,capability,prompt.trim());
      close(); const input=document.getElementById('prompt'); if(input){input.value=prompt.trim();input.focus();input.dispatchEvent(new Event('input'));document.getElementById('chat-form')?.requestSubmit();}
    });
    document.getElementById('new-workspace')?.addEventListener('click',async()=>{ const n=window.prompt('Nombre del espacio'); if(!n?.trim())return; await createWorkspace(n.trim()); hub(); });
  }
  window.BiteyWorkspace={hub,catalog,workspaces};
  window.BiteyUI=window.BiteyUI||{};
  window.BiteyUI.workspace=hub;
  document.addEventListener('DOMContentLoaded',()=>{ document.querySelectorAll('[data-workspace]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();hub();})); });
})();
