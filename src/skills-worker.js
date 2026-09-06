import biteyWorker from './evidence-worker.js';

const SKILLS = new Map([
  ['research', {name:'research', version:'1.0.0', description:'Investigación con planificación, evidencia y fuentes verificables.', domain:'research', capabilities:['research','evidence','synthesis'], workflow:['understand_goal','collect_context','research','verify','synthesize'], tools:['search'], success_criteria:['sources_present','claims_grounded'], constraints:['free_only','no_high_impact_actions'], cost_class:'free', enabled:true}],
  ['documents', {name:'documents', version:'1.0.0', description:'Crear y revisar documentos estructurados a partir de contexto y evidencia.', domain:'documents', capabilities:['documents','writing','artifact'], workflow:['understand_goal','outline','draft','verify','deliver'], tools:['workspace_files'], success_criteria:['complete_artifact','verified_content'], constraints:['free_only','human_review_for_high_impact'], cost_class:'free', enabled:true}],
  ['data-analysis', {name:'data-analysis', version:'1.0.0', description:'Analizar datos, detectar patrones y explicar resultados.', domain:'analysis', capabilities:['analysis','data','charts'], workflow:['inspect_data','validate','analyze','cross_check','explain'], tools:['calculator','workspace_files'], success_criteria:['validated_inputs','reproducible_result'], constraints:['free_only','no_external_billing'], cost_class:'free', enabled:true}],
  ['code', {name:'code', version:'1.0.0', description:'Razonamiento y revisión de código sin ejecución arbitraria por defecto.', domain:'code', capabilities:['code','debug','architecture'], workflow:['inspect','reason','propose','verify','deliver'], tools:['code_reasoning','workspace_files'], success_criteria:['actionable_result','no_arbitrary_execution'], constraints:['free_only','sandbox_execution_only'], cost_class:'free', enabled:true}],
  ['jobia', {name:'jobia', version:'1.0.0', description:'Capacidad especializada para trabajo y empleo mediante el contrato JobIA.', domain:'work', capabilities:['employment','jobs','career'], workflow:['understand_goal','match_context','analyze','verify','respond'], tools:['workspace_files'], success_criteria:['relevant_result','verified_constraints'], constraints:['free_only','jobia_contract_only'], cost_class:'free', enabled:true}],
]);

const FORBIDDEN = /skywork|paid[_ -]?api|billing|gemini\s*api/i;
function validateSkill(skill) {
  const errors=[]; const warnings=[];
  if (!skill?.name?.trim()) errors.push('name_required');
  if (!/^\d+\.\d+(?:\.\d+)?$/.test(String(skill?.version||''))) errors.push('invalid_version');
  if (!skill?.objective?.trim() && !skill?.description?.trim()) errors.push('objective_required');
  if (!skill?.domain?.trim()) errors.push('domain_required');
  if (!Array.isArray(skill?.workflow) || !skill.workflow.length) errors.push('workflow_required');
  if (!Array.isArray(skill?.success_criteria) || !skill.success_criteria.length) errors.push('success_criteria_required');
  if (skill?.cost_class !== 'free') errors.push('free_only_required');
  if (FORBIDDEN.test(JSON.stringify(skill))) errors.push('forbidden_dependency');
  if (!Array.isArray(skill?.constraints) || !skill.constraints.length) warnings.push('constraints_not_defined');
  return {valid:!errors.length, errors, warnings};
}
function slug(v){return String(v||'skill').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,48)||'skill'}
function createSkill(body){
  const goal=String(body?.goal||'').trim();
  const name=String(body?.name||`skill-${slug(goal)}`).trim();
  const skill={name,version:'1.0.0',description:`Bitey skill for: ${goal}`,objective:goal,domain:String(body?.domain||'general'),capabilities:Array.isArray(body?.capabilities)?body.capabilities:[],workflow:['understand_goal','collect_relevant_context','plan_solution','execute_allowed_capabilities','verify_result','learn_from_feedback'],tools:Array.isArray(body?.tools)?body.tools:[],success_criteria:['answer_or_artifact_is_complete','result_is_verified','no_forbidden_cost_is_introduced'],constraints:['use_only_declared_capabilities','free_only_by_default','no_high_impact_actions_without_authorization'],cost_class:'free',enabled:true,metadata:{created_by:'bitey-native-skill-engine',created_at:new Date().toISOString()}};
  const validation=validateSkill(skill); if(validation.valid) SKILLS.set(name,skill); return {skill,validation};
}
async function json(data,status=200,headers={}){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8',...headers}})}
export default {
  async fetch(request, env, ctx) {
    const url=new URL(request.url);
    if(url.pathname==='/api/v1/skills' && request.method==='GET') return json({engine:'bitey-native-skill-engine',version:'1.0',free_only_default:true,skywork_dependency:false,skills:[...SKILLS.values()]});
    if(url.pathname==='/api/v1/skills/status' && request.method==='GET') return json({engine:'bitey-native-skill-engine',skills:SKILLS.size,free_only_default:true,skywork_dependency:false,external_provider_dependency:false});
    if(url.pathname==='/api/v1/skills/validate' && request.method==='POST') { try {const body=await request.json(); return json({skill:body,validation:validateSkill(body)});} catch{return json({validation:{valid:false,errors:['invalid_json'],warnings:[]}},400)} }
    if(url.pathname==='/api/v1/skills/create' && request.method==='POST') { try {const result=createSkill(await request.json()); return json(result,result.validation.valid?201:422);} catch{return json({validation:{valid:false,errors:['invalid_json'],warnings:[]}},400)} }
    return biteyWorker.fetch(request,env,ctx);
  }
};
