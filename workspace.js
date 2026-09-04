(() => {
  const MODES = [
    ['chat','◌','General','Conversación y asistencia'],
    ['research','⌕','Deep Research','Investigar con fuentes'],
    ['documents','▤','Documentos','Crear y transformar documentos'],
    ['slides','▥','Slides','Presentaciones editables'],
    ['sheets','▦','Sheets','Datos, tablas y análisis'],
    ['images','◈','Imágenes','Crear y editar contenido visual'],
    ['websites','⌂','Websites','Crear sitios y apps'],
    ['developer','⌘','AI Developer','Código, pruebas y repositorios'],
    ['video','▶','Video','Guiones y producción audiovisual'],
    ['audio','◉','Audio / Podcast','Guiones, voz y estructura'],
    ['skills','✦','Skills','Capacidades y flujos reutilizables'],
    ['automation','↻','Automatizaciones','Tareas programadas y workflows'],
    ['markets','◉','Mercados en vivo','Market Intelligence de Bitey SBT']
  ];
  const prompts = {
    chat:'', research:'Investiga profundamente este tema y presenta fuentes, evidencia, contradicciones y conclusiones:',
    documents:'Crea un documento profesional sobre:', slides:'Crea una presentación profesional sobre:',
    sheets:'Analiza estos datos y crea una estructura de hoja de cálculo:', images:'Crea una propuesta visual para:',
    websites:'Diseña y desarrolla un sitio web completo para:', developer:'Ayúdame a desarrollar, revisar y probar:',
    video:'Diseña el guion y plan de producción de un video sobre:', audio:'Crea un guion de podcast/audio sobre:',
    skills:'Diseña una Skill reutilizable para:', automation:'Diseña una automatización segura para:'
  };
  function esc(v){return String(v).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
  function setMode(mode,label){
    window.BiteyWorkspaceMode=mode;
    const input=document.getElementById('prompt');
    if(input && prompts[mode]){input.value=prompts[mode]+' ';input.dispatchEvent(new Event('input'));input.focus();}
    document.querySelectorAll('[data-workspace-mode]').forEach(b=>b.classList.toggle('active',b.dataset.workspaceMode===mode));
    if(mode==='markets'){window.BiteyUI?.markets();return;}
  }
  function openHub(){
    const body=document.getElementById('modal-body');
    const modal=document.getElementById('modal-backdrop');
    if(!body||!modal)return;
    document.getElementById('modal-title').textContent='Espacio de trabajo Bitey IA';
    document.getElementById('modal-text').textContent='Una sola interfaz para conversar, investigar, crear, analizar y ejecutar trabajo.';
    body.innerHTML='<div class="workspace-grid">'+MODES.map(([id,icon,name,desc])=>`<button class="workspace-card" data-workspace-modal="${esc(id)}"><span class="workspace-icon">${icon}</span><span><b>${name}</b><small>${desc}</small></span></button>`).join('')+'</div>';
    modal.classList.add('open');
    body.querySelectorAll('[data-workspace-modal]').forEach(b=>b.onclick=()=>{const m=b.dataset.workspaceModal;modal.classList.remove('open');setMode(m,b.textContent.trim())});
  }
  function inject(){
    const tools=document.querySelector('.sidebar-tools');
    const label=document.querySelector('.conversations-label');
    if(!tools||!label||document.getElementById('bitey-workspace-nav'))return;
    const section=document.createElement('div');section.id='bitey-workspace-nav';section.className='workspace-nav';
    section.innerHTML='<div class="sidebar-section">Crear y trabajar</div><button class="sidebar-tool workspace-hub" type="button"><span class="tool-icon">✦</span><span>Espacio de trabajo</span></button>'+MODES.map(([id,icon,name,desc])=>`<button class="sidebar-tool workspace-mode" type="button" data-workspace-mode="${id}" title="${esc(desc)}"><span class="tool-icon">${icon}</span><span>${name}</span></button>`).join('');
    label.parentNode.insertBefore(section,label);
    section.querySelector('.workspace-hub').onclick=openHub;
    section.querySelectorAll('[data-workspace-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.workspaceMode,b.textContent.trim()));
    const style=document.createElement('style');style.textContent='.workspace-nav{display:flex;flex-direction:column;gap:2px}.workspace-nav .sidebar-section{margin-top:13px}.workspace-mode{min-height:34px!important}.workspace-mode.active{background:#12303b!important;border-color:#1c4b5b!important;color:#e5f8fb!important}.workspace-hub{background:#111f27!important;border-color:#24414c!important;color:#eaf7fa!important;margin-bottom:2px}.workspace-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.workspace-card{display:flex;align-items:center;gap:10px;text-align:left;padding:12px;border:1px solid #263943;border-radius:12px;background:#111a22;color:#edf5f8;cursor:pointer}.workspace-card:hover{background:#172630;border-color:#34758a}.workspace-icon{width:28px;height:28px;display:grid;place-items:center;border-radius:8px;background:#12303b;color:#5ed4e6;font-size:15px}.workspace-card b{display:block;font-size:12px}.workspace-card small{display:block;color:#7f929e;font-size:9px;margin-top:3px}@media(max-width:560px){.workspace-grid{grid-template-columns:1fr}}';document.head.appendChild(style);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject);else inject();
  window.BiteyWorkspace={modes:MODES,setMode,openHub};
})();
