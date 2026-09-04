(() => {
  const MODES = [
    ['chat','◌','General','Conversación y asistencia'],['research','⌕','Deep Research','Investigar con fuentes'],['documents','▤','Documentos','Crear y transformar documentos'],['slides','▥','Slides','Presentaciones editables'],['sheets','▦','Sheets','Datos, tablas y análisis'],['images','◈','Imágenes','Crear y editar contenido visual'],['websites','⌂','Websites','Crear sitios y apps'],['developer','⌘','AI Developer','Código, pruebas y repositorios'],['video','▶','Video','Guiones y producción audiovisual'],['audio','◉','Audio / Podcast','Guiones y estructura'],['skills','✦','Skills','Capacidades reutilizables'],['automation','↻','Automatizaciones','Workflows programados'],['markets','◉','Mercados en vivo','Market Intelligence de Bitey SBT']
  ];
  const prompts={chat:'',research:'Investiga profundamente este tema y presenta fuentes, evidencia, contradicciones y conclusiones:',documents:'Crea un documento profesional sobre:',slides:'Crea una presentación profesional sobre:',sheets:'Analiza estos datos y crea una estructura de hoja de cálculo:',images:'Crea una propuesta visual para:',websites:'Diseña y desarrolla un sitio web completo para:',developer:'Ayúdame a desarrollar, revisar y probar:',video:'Diseña el guion y plan de producción de un video sobre:',audio:'Crea un guion de podcast/audio sobre:',skills:'Diseña una Skill reutilizable para:',automation:'Diseña una automatización segura para:'};
  const esc=v=>String(v).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  let activeTask=null;
  function setMode(mode){
    window.BiteyWorkspaceMode=mode;
    const input=document.getElementById('prompt');
    if(input&&prompts[mode]){input.value=prompts[mode]+' ';input.dispatchEvent(new Event('input'));input.focus();}
    document.querySelectorAll('[data-workspace-mode]').forEach(b=>b.classList.toggle('active',b.dataset.workspaceMode===mode));
    if(mode==='markets'){window.BiteyUI?.markets();return;}
    openPanel();
  }
  function panel(){return document.getElementById('bitey-workspace-panel');}
  function renderPanel(){
    const p=panel();if(!p)return;
    const t=activeTask;
    p.innerHTML=`<div class="bwp-head"><div><small>BITEY WORKSPACE</small><h3>${t?esc(t.title):'Centro de trabajo'}</h3></div><button id="bwp-close" aria-label="Cerrar">×</button></div>
      ${t?`<div class="bwp-status"><span class="bwp-dot ${t.status}"></span>${t.statusLabel} <b>${t.progress}%</b></div><div class="bwp-progress"><i style="width:${t.progress}%"></i></div>
      <div class="bwp-section"><b>Actividad</b>${t.steps.map(s=>`<div class="bwp-step ${s.done?'done':''}"><span>${s.done?'✓':'○'}</span>${esc(s.label)}</div>`).join('')}</div>
      <div class="bwp-section"><b>Resultados</b><div class="bwp-artifacts">${t.artifacts.map(a=>`<button class="bwp-artifact"><span>${a.icon}</span><div><strong>${esc(a.name)}</strong><small>${esc(a.type)}</small></div></button>`).join('')}</div></div>`
      :`<div class="bwp-empty"><div class="bwp-empty-icon">✦</div><strong>Un workspace, una tarea</strong><p>Describe lo que quieres hacer. Bitey puede investigar, razonar y preparar varios resultados dentro de la misma tarea.</p><div class="bwp-example">“Investiga el mercado de IA y prepara informe + presentación + hoja de cálculo.”</div></div>`}`;
    document.getElementById('bwp-close').onclick=()=>p.classList.remove('open');
  }
  function openPanel(){const p=panel();if(p){p.classList.add('open');renderPanel();}}
  function startTask(text){
    if(!text||text.trim().length<2)return;
    const low=text.toLowerCase();
    const artifacts=[];
    if(/informe|documento|report|pdf|docx/.test(low))artifacts.push({icon:'▤',name:'Documento / informe',type:'Documento'});
    if(/presentaci|slides|ppt|powerpoint/.test(low))artifacts.push({icon:'▥',name:'Presentación',type:'Slides'});
    if(/hoja|excel|spreadsheet|xlsx|datos/.test(low))artifacts.push({icon:'▦',name:'Hoja de cálculo',type:'Sheets'});
    if(/imagen|visual|logo/.test(low))artifacts.push({icon:'◈',name:'Recurso visual',type:'Imagen'});
    if(/sitio|website|web|app/.test(low))artifacts.push({icon:'⌂',name:'Sitio / aplicación',type:'Website'});
    if(!artifacts.length)artifacts.push({icon:'◌',name:'Respuesta de Bitey',type:'Resultado'});
    if(/investiga|research|analiza|mercado|fuentes/.test(low))artifacts.unshift({icon:'⌕',name:'Investigación y fuentes',type:'Evidence'});
    activeTask={title:text.trim().slice(0,72),status:'running',statusLabel:'Ejecutando tarea',progress:20,steps:[{label:'Interpretar solicitud',done:true},{label:'Seleccionar capacidades',done:true},{label:/investiga|research|fuentes|analiza/.test(low)?'Investigar y contrastar evidencia':'Preparar razonamiento',done:false},{label:'Generar resultados',done:false},{label:'Evaluar y finalizar',done:false}],artifacts};
    openPanel();
    setTimeout(()=>{if(activeTask){activeTask.progress=55;activeTask.steps[2].done=true;renderPanel();}},900);
    setTimeout(()=>{if(activeTask){activeTask.progress=82;activeTask.steps[3].done=true;renderPanel();}},2200);
    setTimeout(()=>{if(activeTask){activeTask.progress=100;activeTask.status='completed';activeTask.statusLabel='Tarea completada';activeTask.steps[4].done=true;renderPanel();}},4200);
  }
  function openHub(){
    const body=document.getElementById('modal-body'),modal=document.getElementById('modal-backdrop');if(!body||!modal)return;
    document.getElementById('modal-title').textContent='Espacio de trabajo Bitey IA';document.getElementById('modal-text').textContent='Conversación, investigación, creación y ejecución en un mismo workspace.';
    body.innerHTML='<div class="workspace-grid">'+MODES.map(([id,icon,name,desc])=>`<button class="workspace-card" data-workspace-modal="${esc(id)}"><span class="workspace-icon">${icon}</span><span><b>${name}</b><small>${desc}</small></span></button>`).join('')+'</div>';
    modal.classList.add('open');body.querySelectorAll('[data-workspace-modal]').forEach(b=>b.onclick=()=>{modal.classList.remove('open');setMode(b.dataset.workspaceModal);});
  }
  function inject(){
    const tools=document.querySelector('.sidebar-tools'),label=document.querySelector('.conversations-label');if(!tools||!label||document.getElementById('bitey-workspace-nav'))return;
    const section=document.createElement('div');section.id='bitey-workspace-nav';section.className='workspace-nav';section.innerHTML='<div class="sidebar-section">Crear y trabajar</div><button class="sidebar-tool workspace-hub" type="button"><span class="tool-icon">✦</span><span>Espacio de trabajo</span></button>'+MODES.map(([id,icon,name,desc])=>`<button class="sidebar-tool workspace-mode" type="button" data-workspace-mode="${id}" title="${esc(desc)}"><span class="tool-icon">${icon}</span><span>${name}</span></button>`).join('');
    label.parentNode.insertBefore(section,label);section.querySelector('.workspace-hub').onclick=openHub;section.querySelectorAll('[data-workspace-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.workspaceMode));
    const p=document.createElement('aside');p.id='bitey-workspace-panel';p.setAttribute('aria-label','Bitey workspace task panel');document.body.appendChild(p);
    const style=document.createElement('style');style.textContent=`
      .workspace-nav{display:flex;flex-direction:column;gap:2px}.workspace-nav .sidebar-section{margin-top:13px}.workspace-mode{min-height:34px!important}.workspace-mode.active{background:#12303b!important;border-color:#1c4b5b!important;color:#e5f8fb!important}.workspace-hub{background:#111f27!important;border-color:#24414c!important;color:#eaf7fa!important;margin-bottom:2px}.workspace-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.workspace-card{display:flex;align-items:center;gap:10px;text-align:left;padding:12px;border:1px solid #263943;border-radius:12px;background:#111a22;color:#edf5f8;cursor:pointer}.workspace-card:hover{background:#172630;border-color:#34758a}.workspace-icon{width:28px;height:28px;display:grid;place-items:center;border-radius:8px;background:#12303b;color:#5ed4e6;font-size:15px}.workspace-card b{display:block;font-size:12px}.workspace-card small{display:block;color:#7f929e;font-size:9px;margin-top:3px}
      #bitey-workspace-panel{position:fixed;z-index:80;top:0;right:0;width:min(390px,92vw);height:100vh;background:#0b1218;border-left:1px solid #20313a;box-shadow:-18px 0 45px rgba(0,0,0,.35);transform:translateX(105%);transition:transform .24s ease;color:#e8f2f5;font-family:inherit;overflow:auto}#bitey-workspace-panel.open{transform:translateX(0)}.bwp-head{display:flex;justify-content:space-between;gap:14px;padding:22px 20px 16px;border-bottom:1px solid #1d2c34}.bwp-head small{font-size:9px;letter-spacing:1.5px;color:#63c9dc}.bwp-head h3{font-size:16px;margin:5px 0 0;line-height:1.3}.bwp-head button{border:0;background:transparent;color:#82959e;font-size:25px;cursor:pointer}.bwp-status{display:flex;align-items:center;gap:8px;padding:18px 20px 8px;font-size:12px;color:#9bb0b8}.bwp-status b{margin-left:auto;color:#e7f7fa}.bwp-dot{width:8px;height:8px;border-radius:50%;background:#5ed4e6}.bwp-dot.completed{background:#75d69a}.bwp-progress{height:4px;margin:0 20px;background:#17262e;border-radius:99px;overflow:hidden}.bwp-progress i{display:block;height:100%;background:#5ed4e6;transition:width .3s}.bwp-section{padding:18px 20px;border-bottom:1px solid #18272f}.bwp-section>b{font-size:11px;color:#8299a3;text-transform:uppercase;letter-spacing:.8px}.bwp-step{display:flex;gap:10px;align-items:center;margin-top:13px;font-size:12px;color:#8ea1aa}.bwp-step.done{color:#d9edf1}.bwp-step span{width:16px;text-align:center;color:#5ed4e6}.bwp-artifacts{display:grid;gap:8px;margin-top:12px}.bwp-artifact{display:flex;align-items:center;gap:12px;text-align:left;border:1px solid #22343d;background:#101b22;color:#e6f2f4;padding:11px;border-radius:10px;cursor:pointer}.bwp-artifact>span{font-size:18px;color:#61ccde}.bwp-artifact strong,.bwp-artifact small{display:block}.bwp-artifact strong{font-size:12px}.bwp-artifact small{font-size:10px;color:#71868f;margin-top:3px}.bwp-empty{padding:60px 24px;text-align:center;color:#8da0a9}.bwp-empty-icon{margin:0 auto 14px;width:52px;height:52px;border-radius:16px;display:grid;place-items:center;background:#12303b;color:#64d1e4;font-size:24px}.bwp-empty strong{display:block;color:#e5f2f5;font-size:15px}.bwp-empty p{font-size:12px;line-height:1.6}.bwp-example{margin-top:18px;padding:12px;border:1px solid #233740;border-radius:10px;text-align:left;font-size:11px;color:#b3c5cb;background:#101a21}@media(max-width:700px){#bitey-workspace-panel{width:100vw}}
    `;document.head.appendChild(style);
    const form=document.querySelector('form');if(form){form.addEventListener('submit',()=>{const input=document.getElementById('prompt');if(input?.value)startTask(input.value);},true);}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',inject);else inject();
  window.BiteyWorkspace={modes:MODES,setMode,openHub,openPanel,startTask,getTask:()=>activeTask};
})();
