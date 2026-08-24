(() => {
  const serviceMap={
    computers:{title:'Diagnóstico de computador',prompt:'Quero diagnosticar um computador ou notebook. Faça perguntas sobre sintomas, modelo, sistema e urgência.'},
    networks:{title:'Diagnóstico de rede e Wi‑Fi',prompt:'Quero diagnosticar uma rede ou Wi‑Fi. Pergunte sobre alcance, velocidade, dispositivos, roteador e falhas.'},
    servers:{title:'Diagnóstico de servidores',prompt:'Quero avaliar servidores e infraestrutura. Pergunte sobre Windows/Linux, virtualização, backup, armazenamento e disponibilidade.'},
    mobiles:{title:'Diagnóstico de celular',prompt:'Quero diagnosticar um celular. Pergunte sobre modelo, sintomas, bateria, tela, sistema e dados.'},
    cctv:{title:'Diagnóstico de CFTV',prompt:'Quero avaliar uma instalação de CFTV. Pergunte sobre câmeras, DVR/NVR, rede, armazenamento e cobertura.'},
    support:{title:'Diagnóstico de suporte técnico',prompt:'Preciso de suporte técnico. Faça um diagnóstico guiado e determine a melhor próxima ação.'},
    ai:{title:'Diagnóstico de IA empresarial',prompt:'Quero implementar IA na minha empresa. Faça um diagnóstico guiado sobre negócio, processos, atendimento, dados, canais e automações.'}
  };
  window.BiteyDiagnostics={
    open(key){const d=serviceMap[key]||serviceMap.ai;const input=document.querySelector('#prompt');if(input){input.value=d.prompt;input.focus();}document.querySelector('#activity-text')?.replaceChildren(document.createTextNode(d.title));document.querySelector('.chat-area')?.scrollIntoView({behavior:'smooth'});},
    serviceMap
  };
  document.addEventListener('click',e=>{const b=e.target.closest('[data-bitey-diagnostic]');if(!b)return;e.preventDefault();window.BiteyDiagnostics.open(b.dataset.biteyDiagnostic);});
})();