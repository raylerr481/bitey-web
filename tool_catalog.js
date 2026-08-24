(() => {
  const API='/api/v1/capabilities';
  const icon={web_research:'⌕',workspace_files:'▣',calculator:'∑',code_reasoning:'⌘'};
  const label={web_research:'Búsqueda e investigación web',workspace_files:'Archivos y proyectos',calculator:'Calculadora',code_reasoning:'Razonamiento de código'};
  window.BiteyToolCatalog=async function(){
    try{const r=await fetch(API,{headers:{Accept:'application/json'}});if(!r.ok)throw new Error(r.status);const d=await r.json();return Array.isArray(d.tools)?d.tools:[]}catch{return []}
  };
  window.BiteyToolIcon=n=>icon[n]||'✦';
  window.BiteyToolLabel=n=>label[n]||n;
})();
