// Bitey Trainer contract: keep evaluation separate from storage and channel logic.
// This module creates a sanitized training candidate only after a response has passed
// the cognitive validation layer. Persistent storage belongs to the authoritative backend.

export function buildTrainingCandidate({ message = '', answer = '', route = {}, validation = {}, sources = [], teacherTraining = {} } = {}) {
  const text = String(answer || '').trim();
  if (!text || validation?.valid === false || validation?.unsupported_research_answer) return null;
  const sourceRefs = Array.isArray(sources) ? sources.slice(0, 8).map(source => ({
    title: String(source?.title || '').slice(0, 180),
    url: String(source?.url || '').slice(0, 500)
  })).filter(source => source.title || source.url) : [];
  return {
    schema_version: 'trainer-candidate-v1',
    task: String(message || '').trim().slice(0, 1000),
    intent: String(route?.intent || 'general').slice(0, 120),
    strategy: String(route?.tool_step || route?.evidence_method || 'general-reasoning').slice(0, 240),
    validated_answer: text.slice(0, 6000),
    evidence_refs: sourceRefs,
    scores: {
      judge_score: Number.isFinite(Number(teacherTraining?.judge_score)) ? Number(teacherTraining.judge_score) : null,
      evidence_score: Number.isFinite(Number(teacherTraining?.evidence_score)) ? Number(teacherTraining.evidence_score) : null,
      agreement_score: Number.isFinite(Number(teacherTraining?.agreement_score)) ? Number(teacherTraining.agreement_score) : null
    },
    created_at: new Date().toISOString()
  };
}

export function shouldLearn(candidate) {
  return Boolean(candidate && candidate.validated_answer && candidate.schema_version === 'trainer-candidate-v1');
}
