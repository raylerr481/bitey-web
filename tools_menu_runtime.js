(() => {
  const API='/api/v1/capabilities';
  const icons={web_research:'⌕',workspace_files:'▣',calculator:'∑',code_reasoning:'⌘'};
  const labels={web_research:'Búsqueda e investigación web',workspace_files:'Archivos y proyectos',calculator:'Calculadora',code_reasoning:'Razonamiento de código'};
  window.BiteyToolsMenu=async function(open,body,close){
    let items=[];
    try{const r=await fetch(API,{headers:{Accept:'application/json'}});if(r.ok){const d=await r.json();items=Array.isArray(d.tools)?d.tools:[]}}catch{}
    if(!items.length)items=[{name:'web_research',description:'Investiga fuentes públicas y recupera evidencia.'},{name:'workspace_files',description:'Usa archivos y proyectos como contexto general.'},{name:'calculator',description:'Calcula expresiones matemáticas de forma segura y local.'},{name:'code_reasoning',description:'Analiza código sin ejecutar código arbitrario.'}];
    open('Herramientas','Capacidades del Supracerebro disponibles.',`<div class="feature-list">${items.map(t=>`<button class="feature-row" data-tool="${String(t.name).replace(/[^a-z0-9_]/gi,'')}"><span>${icons[t.name]||'✦'}</span><span><b>${labels[t.name]||t.name}</b><small>${t.description||'Herramienta general de Bitey IA'} · Disponible</small></span></button>`).join('')}</div><p class="muted">Bitey puede seleccionar automáticamente la herramienta adecuada para cada tarea.</p>`);
    body().querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{window.BiteyTools=window.BiteyTools||{};window.BiteyTools[b.dataset.tool]=true;close();if(b.dataset.tool==='workspace_files')document.getElementById('file-input')?.click()});
  };
})();
