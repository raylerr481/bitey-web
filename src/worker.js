const AI_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const NO_PROVIDER_ANSWER = 'Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos.';
const LEGACY_NO_PROVIDER_ANSWER = 'No pude obtener una respuesta de Bitey IA en este momento. Inténtalo nuevamente en unos momentos.';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();
    if (url.pathname === '/api/diagnostics/edge-ai' && request.method === 'GET') return runEdgeAiDiagnostic(env, requestId);
    if (url.pathname.startsWith('/api/')) {
      const origin = env.BITEY_BACKEND_ORIGIN;
      if (!origin) return jsonError('Bitey backend origin is not configured', 500, requestId);
      const upstreamUrl = new URL(url.pathname + url.search, origin);
      const headers = new Headers(request.headers);
      headers.set('x-bitey-channel', 'web'); headers.set('x-bitey-origin', 'cloudflare'); headers.set('x-forwarded-host', url.host); headers.set('x-request-id', requestId); headers.delete('host');
      const canUseAiFallback = request.method === 'POST' && url.pathname.includes('/conversations/') && url.pathname.endsWith('/messages');
      const requestClone = canUseAiFallback ? request.clone() : null;
      try {
        const upstream = await fetch(upstreamUrl, { method: request.method, headers, body: ['GET','HEAD'].includes(request.method) ? undefined : request.body, redirect: 'follow' });
        if (canUseAiFallback && env.AI) {
          const fallback = await tryRealAiFallback(upstream, requestClone, env, requestId, origin);
          if (fallback) return fallback;
        }
        const responseHeaders = new Headers(upstream.headers); responseHeaders.set('Cache-Control','no-store'); responseHeaders.set('X-Bitey-Edge','cloudflare'); responseHeaders.set('X-Bitey-Request-Id',requestId);
        return new Response(upstream.body,{status:upstream.status,statusText:upstream.statusText,headers:responseHeaders});
      } catch (error) {
        console.error('Bitey upstream proxy error',{requestId,path:url.pathname,error:String(error)});
        if (canUseAiFallback && env.AI && requestClone) { const fallback=await runRealAiFallback(requestClone,env,requestId,error,origin); if(fallback)return fallback; }
        return jsonError('Bitey backend is temporarily unavailable',502,requestId);
      }
    }
    return env.ASSETS.fetch(request);
  }
};

async function runEdgeAiDiagnostic(env, requestId) {
  if (!env.AI) return jsonError('Workers AI binding is unavailable',503,requestId);
  try {
    const response=await env.AI.run(AI_MODEL,{messages:[{role:'system',content:'Responde únicamente con el resultado de la operación solicitada.'},{role:'user',content:'¿Cuánto es 2+2?'}],max_tokens:32,temperature:0,chat_template_kwargs:{enable_thinking:false}});
    const answer=extractAiText(response); if(!answer){console.error('Workers AI diagnostic returned no text',{requestId,response:safeAiShape(response)});return jsonError('Workers AI returned an empty response',502,requestId);}
    return jsonResponse({ok:true,selected_provider:'cloudflare-workers-ai',model:AI_MODEL,answer,request_id:requestId},200,'cloudflare-ai-diagnostic',requestId);
  } catch(error){console.error('Bitey Workers AI diagnostic failed',{requestId,error:String(error)});return jsonError('Workers AI model execution failed',502,requestId);}
}

async function tryRealAiFallback(upstream, request, env, requestId, origin) {
  if (!request) return null;
  let degraded = !upstream.ok;
  try {
    const raw = await upstream.clone().text();
    let body = null;
    try { body = JSON.parse(raw); } catch (_) {}
    const answer=String(body?.answer||'').trim();
    const providers=Array.isArray(body?.providers) ? body.providers : [];
    degraded = degraded || !answer || !providers.length || answer === NO_PROVIDER_ANSWER || answer === LEGACY_NO_PROVIDER_ANSWER || answer.includes(NO_PROVIDER_ANSWER) || answer.includes(LEGACY_NO_PROVIDER_ANSWER) || answer.startsWith('Ahora mismo no puedo completar esta consulta') || answer.startsWith('No pude obtener una respuesta de Bitey IA');
    if (!degraded) return null;
  } catch (_) {
    degraded = true;
  }
  return runRealAiFallback(request,env,requestId,new Error(`backend_status_${upstream.status}`),origin);
}

async function runRealAiFallback(request, env, requestId, cause, origin) {
  if (!env.AI) return null;
  let payload;
  try { payload=await request.clone().json(); } catch (error) { console.error('Bitey edge fallback could not parse request',{requestId,error:String(error)}); return null; }
  const message=String(payload?.message||'').trim();
  const conversationId=String(request.url).match(/conversations\/([^/]+)\/messages/)?.[1]||'';
  if(!message)return null;

  let history=[];
  if (conversationId) history=await loadConversationHistory(origin,conversationId,requestId);
  const compactHistory=history.slice(-8).map(item=>({role:item.role,content:String(item.content||'').slice(-800)})).filter(item=>item.content&&(item.role==='user'||item.role==='assistant'));
  const system='Eres Bitey IA, una inteligencia general. Responde en el idioma del usuario. Sé útil, clara y honesta. No inventes datos. Mantén continuidad con el historial disponible. Si la consulta requiere información actual o evidencia externa y no tienes esa evidencia, dilo claramente.';
  const messages=[{role:'system',content:system},...compactHistory,{role:'user',content:message}];

  const attempts=[
    {messages,max_tokens:512},
    {messages:[{role:'system',content:system},{role:'user',content:message}],max_tokens:512}
  ];
  for (let index=0; index<attempts.length; index++) {
    try {
      const response=await env.AI.run(AI_MODEL,{messages:attempts[index].messages,max_tokens:attempts[index].max_tokens,temperature:0.2,chat_template_kwargs:{enable_thinking:false}});
      const answer=extractAiText(response);
      if(!answer) throw new Error('empty_response');
      return jsonResponse({conversation_id:conversationId,answer,research_required:false,research_reasons:[],providers:[AI_MODEL],selected_provider:'cloudflare-workers-ai',elapsed_ms:null,activity_events:[index===0 && compactHistory.length?'Generación de recuperación realizada por un modelo de lenguaje real de Cloudflare Workers AI con contexto compacto.':'Generación de recuperación realizada por un modelo de lenguaje real de Cloudflare Workers AI.'],request_id:requestId},200,'cloudflare-ai-fallback',requestId);
    } catch(error) {
      console.error('Bitey Workers AI fallback attempt failed',{requestId,attempt:index+1,cause:String(cause),error:String(error)});
    }
  }
  return null;
}

async function loadConversationHistory(origin, conversationId, requestId) {
  if(!origin||!conversationId)return [];
  try { const url=new URL(`/api/v1/conversations/${encodeURIComponent(conversationId)}/messages`,origin); const response=await fetch(url,{method:'GET',headers:{'Accept':'application/json','x-bitey-channel':'web','x-bitey-origin':'cloudflare','x-request-id':requestId}}); if(!response.ok)return []; const body=await response.json(); return Array.isArray(body?.messages)?body.messages.slice(-8):[]; }
  catch(error){console.warn('Bitey edge could not load conversation history',{requestId,error:String(error)});return [];} 
}

function extractAiText(response){ if(!response)return ''; const direct=response.response??response.result; if(typeof direct==='string'&&direct.trim())return direct.trim(); const choice=response.choices?.[0]; const content=choice?.message?.content??choice?.text; if(typeof content==='string'&&content.trim())return content.trim(); if(Array.isArray(content))return content.map(part=>typeof part==='string'?part:part?.text||'').join('').trim(); return ''; }
function safeAiShape(response){ if(!response||typeof response!=='object')return typeof response; return {keys:Object.keys(response),has_choices:Array.isArray(response.choices),has_response:typeof response.response==='string',has_result:typeof response.result==='string'}; }
function jsonResponse(body,status,edgeHeader,requestId){return new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Bitey-Edge':edgeHeader,'X-Bitey-Request-Id':requestId}});}
function jsonError(message,status,requestId){return jsonResponse({error:message,request_id:requestId},status,'cloudflare',requestId);}
