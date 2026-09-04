(() => {
  const API = () => `${window.BITEY_API_BASE || ''}/api/v1`;
  const esc = s => String(s ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const modal = () => document.getElementById('modal-backdrop');
  const body = () => document.getElementById('modal-body');
  const open = (title, text, html='') => { const m=modal(); if(!m)return; document.getElementById('modal-title').textContent=title; document.getElementById('modal-text').textContent=text; body().innerHTML=html; m.classList.add('open'); };
  async function catalog(){ try{ const r=await fetch(`${API()}/workspace/catalog`); return r.ok?await r.json():null; }catch{return null;} }
  async function workspaces(){ try{ const r=await fetch(`${API()}/workspaces`); return r.ok?(await r.json()).workspaces||[]:[]; }catch{return [];} }
  async function createWorkspace(name){ try{ const r=await fetch(`${API()}/workspaces`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); return r.ok?r.json():null; }catch{return null;} }
  async function inspectCognitive(prompt, capability, context={}){ try{ const r=await fetch(`${API()}/workspace/cognitive/inspect`,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({prompt,capability,context})}); return r.ok?await r.json():null; }catch{return null;} }
  async function createTask(id, capability, prompt, metadata={}){ try{ const r=await fetch(`${API()}/workspaces/${encodeURIComponent(id)}/tasks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:prompt.slice(0,80)||'Nueva tarea',prompt,capability,metadata})}); return r.ok?r.json():null; }catch{return null;} }
  async function runTask(id, taskId){ try{ const r=await fetch(`${API()}/workspaces/${encodeURIComponent(id)}/tasks/${encodeURIComponent(taskId)}/run`,{method:'POST',headers:{'Accept':'application/json'}}); return r.ok?r.json():null; }catch{return null;} }
  async function recentTasks(id){ try{ const r=await fetch(`${API()}/workspaces/${encodeURIComponent(id)}/tasks`); return r.ok?(await r.json()).tasks||[]:[]; }catch{return [];} }
  function phaseMarkup(plan, phase='planning'){
    const phases=['Pensando','Planificando','Investigando','Generando','Evaluando','Listo'];
    const active=phase==='researching'?2:phase==='generating'?3:phase==='evaluating'?4:phase==='completed'?5:1;
    return `<div class="workspace-cognitive-status"><div class="feature-row"><span>◈</span><span><b>Cerebro cognitivo de Bitey</b><small>${esc(plan?.route==='research'?'Ruta: investigación':plan?.route==='artifact'?'Ruta: creación de artefacto':'Ruta: conversación')}</small></span></div><div class="workspace-phases">${phases.map((p,i)=>`<span class="${i<active?'done ':''}${i===active?'active':''}">${i<active?'✓ ':''}${p}</span>`).join('')}</div></div>`;
  }
  function traceMarkup(trace){ return `<details class="workspace-trace"><summary>Ver ejecución cognitiva</summary><div>${(Array.isArray(trace)?trace:[]).map(x=>`<div class="feature-row"><span>${x.status==='blocked'?'⛔':x.status==='skipped'?'—':'✓'}</span><span><b>${esc(x.phase)}</b><small>${esc(x.detail||x.status)}</small></span></div>`).join('')}</div></details>`; }
  function artifactContent(artifact){ const c=artifact?.content; if(c&&typeof c==='object') return String(c.content||JSON.stringify(c,null,2)); return String(c||''); }
  function artifactResult(task){ const a=task?.result?.artifact || task?.result?.artifacts?.[0]; const type=a?.artifact_type||'artifact'; const labels={document:'Documento',presentation:'Presentación',spreadsheet:'Hoja de cálculo',code:'Código'}; return `<div class="workspace-result">${phaseMarkup(task.cognitive_plan||{},'completed')}<div class="feature-row"><span>✓</span><span><b>${esc(labels[type]||'Artefacto')} listo</b><small>${esc(a?.status||'ready')} · evaluación: ${esc(task?.result?.evaluation?.decision||'unknown')}</small></span></div><pre class="workspace-evidence">${esc(artifactContent(a).slice(0,20000)||'El artefacto no contiene contenido visible.')}</pre>${traceMarkup(task?.result?.execution_trace)}</div>`; }
  function researchResult(task){ const result=task?.result||{}; const research=result.research||{}; const evidence=String(research.evidence_context||''); const steps=Array.isArray(research.steps)?research.steps:[]; const sources=steps.flatMap(s=>Array.isArray(s.sources)?s.sources:[]); return `<div class="workspace-result">${phaseMarkup(task.cognitive_plan||{},'completed')}<div class="feature-row"><span>✓</span><span><b>${esc(task.status==='completed'?'Investigación completada':'Investigación sin evidencia suficiente')}</b><small>${steps.length} pasos acotados · ${sources.length} fuentes registradas</small></span></div><pre class="workspace-evidence">${esc(evidence.slice(0,12000)||'Bitey no recuperó evidencia utilizable.')}</pre>${traceMarkup(result.execution_trace)}</div>`; }
  function taskHistoryMarkup(items){ return `<div class="workspace-history"><b>Actividad reciente</b>${(items||[]).slice(0,8).map(t=>`<button class="workspace-task-row" data-task-id="${esc(t.id||'')}"><span>${t.status==='completed'?'✓':t.status==='failed'?'⛔':'◌'}</span><span><b>${esc(t.title||t.prompt||'Tarea')}</b><small>${esc(t.status||'queued')} · ${esc(t.capability||'general')}</small></span></button>`).join('')||'<small>No hay tareas todavía.</small>'}</div>`; }
  async function executeFromWorkspace(capability,prompt,current,options={}){
    const plan=await inspectCognitive(prompt,capability,{workspace:true,workspace_id:current?.id,...(options.context||{})});
    if(!plan) return {ok:false,error:'cognitive_contract_unavailable'};
    let w=current; if(!w){ const list=await workspaces(); w=list[0] || await createWorkspace('Espacio general'); }
    if(!w) return {ok:false,error:'workspace_unavailable',plan};
    const task=await createTask(w.id,capability,prompt,options.metadata||{});
    if(!task) return {ok:false,error:'task_creation_failed',plan,workspace:w};
    const executed=await runTask(w.id,task.id);
    if(!executed) return {ok:false,error:'task_execution_failed',plan,workspace:w,task};
    executed.cognitive_plan=plan;
    return {ok:true,plan,workspace:w,task:executed};
  }
  async function executeAndOpen(capability,prompt,current){
    const result=await executeFromWorkspace(capability,prompt,current);
    if(!result.ok){ open('Workspace de Bitey IA','No se pudo completar la ejecución cognitiva.'); return result; }
    const task=result.task;
    if(capability==='deep_research'||capability==='browser_research') open('Investigación de Bitey IA','Bitey ejecutó una investigación acotada y verificable.',researchResult(task));
    else if(['documents','slides','spreadsheets','code'].includes(capability)) open('Artefacto de Bitey IA','Bitey completó la generación y evaluación.',artifactResult(task));
    else open('Resultado de Bitey IA','Bitey completó la tarea.',`<div class="workspace-result">${phaseMarkup(result.plan,'completed')}<pre class="workspace-evidence">${esc(String(task.result?.answer||task.result?.content||''))}</pre>${traceMarkup(task.result?.execution_trace)}</div>`);
    return result;
  }
  async function hub(){
    const [c, ws] = await Promise.all([catalog(), workspaces()]);
    const caps = c?.capabilities || [{id:'chat',label:'Chat',kind:'conversation'},{id:'deep_research',label:'Investigación profunda',kind:'research'},{id:'documents',label:'Documentos',kind:'artifact'},{id:'slides',label:'Presentaciones',kind:'artifact'},{id:'spreadsheets',label:'Hojas de cálculo',kind:'artifact'},{id:'code',label:'Código',kind:'artifact'},{id:'files',label:'Archivos',kind:'context'},{id:'agents',label:'Agentes',kind:'orchestration'}];
    const current = ws[0];
    open('Workspace de Bitey IA','Un espacio de trabajo integral para investigar, crear y ejecutar tareas con el cerebro cognitivo de Bitey.',`<div class="workspace-grid">${caps.map(x=>`<button class="workspace-card" data-cap="${esc(x.id)}"><span class="workspace-icon">${x.id==='deep_research'?'✦':x.id==='documents'?'▤':x.id==='slides'?'▥':x.id==='spreadsheets'?'▦':x.id==='code'?'⌘':x.id==='files'?'▣':x.id==='agents'?'◈':'◌'}</span><b>${esc(x.label)}</b><small>${esc(x.kind)}</small></button>`).join('')}</div><div class="workspace-list"><div class="feature-row"><span>◇</span><span><b>${esc(current?.name || 'Espacio general')}</b><small>${ws.length ? `${ws.length} espacios disponibles` : 'Crea tu primer espacio de trabajo'}</small></span></div><button class="primary-action" id="new-workspace">＋ Nuevo espacio</button>${current?taskHistoryMarkup(await recentTasks(current.id)):''}</div>`);
    body()?.querySelectorAll('[data-cap]').forEach(b=>b.onclick=async()=>{ const capability=b.dataset.cap, prompt=window.prompt(`¿Qué quieres hacer con ${b.textContent.trim()}?`); if(!prompt?.trim()) return; await executeAndOpen(capability,prompt,current); });
    document.getElementById('new-workspace')?.addEventListener('click',async()=>{ const n=window.prompt('Nombre del espacio'); if(!n?.trim())return; await createWorkspace(n.trim()); hub(); });
    body()?.querySelectorAll('[data-task-id]').forEach(b=>b.onclick=async()=>{ const tasks=await recentTasks(current?.id); const task=tasks.find(x=>x.id===b.dataset.taskId); if(task) open('Tarea de Bitey IA',`Estado: ${task.status||'queued'}`,`<div class="workspace-result">${phaseMarkup(task.cognitive_plan||{},task.status==='completed'?'completed':'planning')}<pre class="workspace-evidence">${esc(JSON.stringify(task.result||task,null,2).slice(0,20000))}</pre></div>`); });
  }
  window.BiteyWorkspace={hub,catalog,workspaces,inspectCognitive,createTask,runTask,recentTasks,execute:executeFromWorkspace};
  window.BiteyUI=window.BiteyUI||{}; window.BiteyUI.workspace=hub;
  document.addEventListener('DOMContentLoaded',()=>{ document.querySelectorAll('[data-workspace]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();hub();})); });
})();
