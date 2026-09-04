(() => {
  const API = () => `${window.BITEY_API_BASE || ''}/api/v1`;
  const esc = s => String(s ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const modal = () => document.getElementById('modal-backdrop');
  const body = () => document.getElementById('modal-body');
  const open = (title, text, html='') => { const m=modal(); if(!m)return; document.getElementById('modal-title').textContent=title; document.getElementById('modal-text').textContent=text; body().innerHTML=html; m.classList.add('open'); };
  const close = () => modal()?.classList.remove('open');
  const api = async (path, options={}) => { try { const r=await fetch(`${API()}${path}`,options); if(!r.ok)return null; return await r.json(); } catch { return null; } };
  const catalog = () => api('/workspace/catalog');
  const workspaces = async () => (await api('/workspaces'))?.workspaces || [];
  const getWorkspace = id => api(`/workspaces/${encodeURIComponent(id)}`);
  const createWorkspace = name => api('/workspaces',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  const createTask = (id, capability, prompt) => api(`/workspaces/${encodeURIComponent(id)}/tasks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:prompt.slice(0,80)||'Nueva tarea',prompt,capability})});
  const runTask = (id, taskId) => api(`/workspaces/${encodeURIComponent(id)}/tasks/${encodeURIComponent(taskId)}/run`,{method:'POST',headers:{'Accept':'application/json'}});
  const icons = {deep_research:'✦',browser_research:'⌕',documents:'▤',slides:'▥',spreadsheets:'▦',code:'⌘',files:'▣',projects:'◇',agents:'◈',chat:'◌'};
  const descriptions = {
    chat:'Conversación y razonamiento con Bitey.', deep_research:'Investigación acotada con evidencia y fuentes.', browser_research:'Consulta web para obtener información actual.',
    documents:'Redacta documentos y borradores estructurados.', slides:'Prepara presentaciones organizadas por diapositivas.', spreadsheets:'Convierte análisis en estructuras de hoja de cálculo.',
    code:'Genera y analiza código sin ejecución arbitraria.', files:'Trabaja con archivos como contexto del proyecto.', projects:'Organiza contexto, tareas y entregables.', agents:'Orquesta tareas especializadas bajo las reglas de Bitey.'
  };
  function taskForm(cap, workspace) {
    open(cap.label, descriptions[cap.id] || 'Capacidad de Bitey IA.', `<div class="workspace-task-form"><label for="workspace-prompt">¿Qué quieres que haga Bitey?</label><textarea id="workspace-prompt" rows="5" placeholder="Describe el resultado que necesitas..."></textarea><div class="workspace-form-actions"><button class="secondary-action" id="workspace-cancel">Cancelar</button><button class="primary-action" id="workspace-run">Ejecutar con Bitey</button></div></div>`);
    const input=document.getElementById('workspace-prompt'); input?.focus();
    document.getElementById('workspace-cancel')?.addEventListener('click',close);
    document.getElementById('workspace-run')?.addEventListener('click',async()=>{
      const prompt=input?.value?.trim(); if(!prompt)return;
      const button=document.getElementById('workspace-run'); if(button){button.disabled=true;button.textContent='Ejecutando…';}
      const task=await createTask(workspace.id,cap.id,prompt);
      if(!task){open(cap.label,'No se pudo crear la tarea.','<p class="muted">Comprueba que el backend de Bitey IA Web esté disponible.</p>');return;}
      const result=await runTask(workspace.id,task.id);
      if(!result){open(cap.label,'La tarea quedó registrada pero no pudo ejecutarse.');return;}
      renderTaskResult(cap,result);
    });
  }
  function renderTaskResult(cap,task){
    const result=task.result||{}; const evaluation=result.evaluation||{}; const answer=String(result.answer||'');
    const artifact=result.artifact; const research=result.research;
    const meta=[]; if(task.status)meta.push(task.status); if(evaluation.decision)meta.push(`evaluación: ${evaluation.decision}`); if(research?.steps)meta.push(`${research.steps.length} pasos`);
    const artifactHtml=artifact?`<div class="workspace-artifact"><span>${icons[cap.id]||'▤'}</span><div><b>${esc(artifact.name||'Artefacto generado')}</b><small>${esc(artifact.artifact_type||'artifact')} · listo para revisión</small></div></div>`:'';
    const researchHtml=research?`<div class="workspace-research-meta"><b>Investigación</b><span>${Array.isArray(research.steps)?research.steps.length:0} pasos acotados</span></div>`:'';
    open(cap.label,meta.join(' · ')||'Resultado de Bitey IA',`${artifactHtml}${researchHtml}<div class="workspace-answer">${esc(answer||'Bitey no devolvió contenido utilizable.')}</div><div class="workspace-form-actions"><button class="primary-action" id="workspace-done">Cerrar</button></div>`);
    document.getElementById('workspace-done')?.addEventListener('click',close);
  }
  function renderCards(caps,workspace){
    return caps.map(c=>`<button class="workspace-card" data-cap="${esc(c.id)}"><span class="workspace-icon">${icons[c.id]||'◌'}</span><b>${esc(c.label)}</b><small>${esc(descriptions[c.id]||c.kind||'Capacidad de Bitey IA')}</small></button>`).join('');
  }
  async function hub(){
    const [c,ws]=await Promise.all([catalog(),workspaces()]);
    const caps=c?.capabilities||[{id:'chat',label:'Chat',kind:'conversation'},{id:'deep_research',label:'Investigación profunda',kind:'research'},{id:'browser_research',label:'Investigación web',kind:'research'},{id:'documents',label:'Documentos',kind:'artifact'},{id:'slides',label:'Presentaciones',kind:'artifact'},{id:'spreadsheets',label:'Hojas de cálculo',kind:'artifact'},{id:'code',label:'Código',kind:'artifact'},{id:'files',label:'Archivos',kind:'context'},{id:'projects',label:'Proyectos',kind:'workspace'},{id:'agents',label:'Agentes',kind:'orchestration'}];
    let current=ws[0];
    const status=c?.execution||{};
    open('Bitey IA Workspace','Un workspace integral inspirado en la experiencia de las plataformas modernas de IA, implementado dentro de Bitey IA Web.',`<div class="workspace-status"><span class="workspace-status-dot"></span><span>${status.free_only!==false?'Modo gratuito protegido':'Modo de ejecución configurado'}</span><span>·</span><span>${status.paid_fallback===false?'sin fallback de pago':'política definida'}</span></div><div class="workspace-section-title">Capacidades</div><div class="workspace-grid">${renderCards(caps,current)}</div><div class="workspace-section-title">Espacios de trabajo</div><div class="workspace-list"><div class="workspace-current"><span class="workspace-icon">◇</span><div><b>${esc(current?.name||'Espacio general')}</b><small>${ws.length?`${ws.length} espacios disponibles`:'Aún no hay espacios persistentes'}</small></div></div><div class="workspace-form-actions"><button class="secondary-action" id="workspace-refresh">Actualizar</button><button class="primary-action" id="new-workspace">＋ Nuevo espacio</button></div></div>`);
    body()?.querySelectorAll('[data-cap]').forEach(b=>b.addEventListener('click',()=>{const cap=caps.find(x=>x.id===b.dataset.cap)||{id:b.dataset.cap,label:b.dataset.cap}; if(!current){open('Workspace','Crea primero un espacio de trabajo.');return;} taskForm(cap,current);}));
    document.getElementById('workspace-refresh')?.addEventListener('click',hub);
    document.getElementById('new-workspace')?.addEventListener('click',async()=>{const n=window.prompt('Nombre del espacio de Bitey IA');if(!n?.trim())return;const created=await createWorkspace(n.trim());if(created){current=created;hub();}});
  }
  window.BiteyWorkspace={hub,catalog,workspaces,getWorkspace,createTask,runTask};
  window.BiteyUI=window.BiteyUI||{}; window.BiteyUI.workspace=hub;
  document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('[data-workspace]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();hub();})));
})();
