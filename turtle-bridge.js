(()=> {
  const SBT = 'https://bitey-system-bots-trading-api.onrender.com';
  const state = { active:false, last:null };
  const TURTLE_RE = /\b(turtle|tortuga|mt4|metatrader 4|s1|s2|campaign|campa[nñ]a|unidades?|breakout|piramid|n actual|n\/atr|equity|turtle trading)\b/i;

  const esc = v => String(v ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const money = v => Number.isFinite(Number(v)) ? Number(v).toFixed(2) : '—';
  const num = (v,d=5) => Number.isFinite(Number(v)) ? Number(v).toFixed(d) : '—';
  const time = v => { const d=new Date(v); return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(); };

  async function get(path) {
    const r = await fetch(SBT + path, {headers:{Accept:'application/json'}, cache:'no-store'});
    if (!r.ok) throw new Error('SBT HTTP '+r.status);
    return r.json();
  }

  function isFollowUp(text) {
    return state.active && /^(y|e|pero|entonces|ahora|¿?y|y ahora|qué pasa|que pasa|cómo va|como va|cuánto|cuanto|cu[aá]l|cual|dime más|y el|y la|y los|y las)\b/i.test(String(text).trim());
  }

  function turtleIntent(text) {
    return TURTLE_RE.test(text) || isFollowUp(text);
  }

  function renderIntoChat(role, html) {
    const messages=document.querySelector('#messages');
    if(!messages) return;
    if(messages.querySelector('.welcome')) messages.innerHTML='';
    const row=document.createElement('article');
    row.className='message '+role;
    const body=document.createElement('div');
    body.className='message-content';
    body.innerHTML=html;
    row.appendChild(body);
    messages.appendChild(row);
    row.scrollIntoView({behavior:'smooth',block:'end'});
  }

  function answerLatest(s, q) {
    const m=s?.market||{}, a=s?.account||{}, t=s?.turtle||{}, metrics=s?.metrics||{};
    const dir=t.campaign_direction>0?'BUY':t.campaign_direction<0?'SELL':'FLAT';
    const active=Boolean(t.campaign_active);
    const regime=String(s?.regime||'FLAT');
    const units=t.campaign_units ?? 0;
    state.active=true; state.last=s;
    const symbol=s?.symbol||'—';
    return '<h3>🐢 Estado actual del Turtle</h3>'+
      '<p><strong>'+esc(symbol)+'</strong> · '+esc(s?.timeframe||'—')+' · '+esc(s?.mode||'read-only')+'</p>'+
      '<ul>'+
      '<li>Estado: <strong>'+esc(active?dir:'FLAT')+'</strong> · régimen <strong>'+esc(regime)+'</strong></li>'+
      '<li>Campaña: <strong>'+esc(active?('ID '+(t.campaign_id??'—')+' · '+(t.campaign_system===1?'S1':t.campaign_system===2?'S2':'S1/S2')):'sin campaña')+'</strong></li>'+
      '<li>Unidades: <strong>'+esc(units)+'</strong> · N/ATR: <strong>'+num(t.campaign_n ?? m.atr)+'</strong></li>'+
      '<li>Precio: <strong>'+num(m.bid)+'</strong> / '+num(m.ask)+'</li>'+
      '<li>Equity: <strong>'+money(a.equity)+'</strong> · balance: <strong>'+money(a.balance)+'</strong></li>'+
      '<li>Trades abiertos: <strong>'+esc(a.open_trades??'—')+'</strong> · dirección HTF: <strong>'+esc(metrics.htf_direction||'FLAT')+'</strong></li>'+
      '</ul>'+
      '<p><small>Lectura directa desde Bitey SBT · solo lectura · ejecución bloqueada · '+time(s?.timestamp||s?.time)+'</small></p>';
  }

  function answerHistory(items,q) {
    const rows=Array.isArray(items)?items:[];
    if(!rows.length) return '<p>No hay snapshots Turtle disponibles todavía. MT4 debe enviar al gateway al menos un snapshot.</p>';
    const first=rows[0], last=rows[rows.length-1];
    const changes=[];
    for(let i=1;i<rows.length;i++){
      const a=rows[i-1],b=rows[i],at=a?.turtle||{},bt=b?.turtle||{};
      if(String(a?.regime)!==String(b?.regime)) changes.push(time(b.timestamp||b.time)+' · régimen '+String(a?.regime||'—')+' → '+String(b?.regime||'—'));
      if(Number(at?.campaign_units||0)!==Number(bt?.campaign_units||0)) changes.push(time(b.timestamp||b.time)+' · unidades '+(at?.campaign_units??0)+' → '+(bt?.campaign_units??0));
      if(String(at?.campaign_direction)!==String(bt?.campaign_direction)) changes.push(time(b.timestamp||b.time)+' · dirección cambió');
    }
    state.active=true; state.last=last;
    return '<h3>🐢 Historial reciente del Turtle</h3>'+
      '<p>'+rows.length+' snapshots recibidos. Último estado: <strong>'+esc(last?.regime||'FLAT')+'</strong>, unidades <strong>'+esc(last?.turtle?.campaign_units??0)+'</strong>, equity <strong>'+money(last?.account?.equity)+'</strong>.</p>'+
      (changes.length?'<p><strong>Cambios detectados</strong></p><ul>'+changes.slice(-8).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'<p>No se detectaron cambios de campaña/unidades/régimen en la ventana consultada.</p>')+
      '<p><small>Fuente: Bitey SBT · MT4 read-only.</small></p>';
  }

  async function handle(text) {
    const q=String(text||'').trim();
    if(!turtleIntent(q)) return false;
    const activity=document.querySelector('#activity');
    const activityText=document.querySelector('#activity-text');
    if(activity){activity.hidden=false;}
    if(activityText) activityText.textContent='Consultando el estado del Turtle en SBT…';
    try {
      if(/\b(historial|últim[oa]s?|ultimos|evoluci[oó]n|últimas? horas|cambios|ha hecho)\b/i.test(q)){
        const d=await get('/api/v1/mt4/bitey-history?limit=20');
        renderIntoChat('assistant',answerHistory(d?.snapshots||d?.history||[],q));
      } else {
        const d=await get('/api/v1/mt4/bitey-latest');
        const s=d?.snapshot||d;
        if(!s || (!s.symbol && !s.market && !s.turtle)) {
          renderIntoChat('assistant','<p>El gateway SBT todavía no tiene un snapshot Turtle válido de MT4. No voy a inventar el estado.</p><p><small>Cuando MT4 envíe el primer snapshot, aquí podrás preguntar por estado, campaña, unidades, N, precio y equity.</small></p>');
          state.active=true;
        } else {
          renderIntoChat('assistant',answerLatest(s,q));
        }
      }
    } catch(e) {
      renderIntoChat('assistant','<p>No pude consultar Bitey SBT ahora mismo. El canal Turtle es <strong>solo lectura</strong>; no se enviará ninguna orden a MT4.</p>');
      console.warn('[Bitey Turtle bridge]',e);
    } finally {
      if(activity) activity.hidden=true;
    }
    return true;
  }

  document.addEventListener('submit', e => {
    const form=e.target;
    if(form?.id!=='chat-form') return;
    const input=document.querySelector('#prompt');
    const q=String(input?.value||'').trim();
    if(!turtleIntent(q)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    void handle(q).then(()=>{if(input){input.value='';input.style.height='auto';input.focus();}});
  }, true);

  window.BiteyTurtleBridge={handle,isTurtleIntent:turtleIntent};
})();