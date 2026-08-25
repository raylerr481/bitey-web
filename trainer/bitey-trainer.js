/**
 * Bitey Trainer — internal capability of Bitey IA.
 *
 * This module is intentionally independent from BiteFixes business logic.
 * BiteFixes consumes Trainer through an authorized API/contract; Trainer
 * remains part of the general Bitey IA project.
 */

export const TRAINER_VERSION = "1.0.0";

export const HUMAN_REQUIRED_TASKS = Object.freeze([
  "identity_verification",
  "voice_recording",
  "photo_or_video_capture",
  "legal_acceptance",
  "payment_authorization",
  "platform_requires_human"
]);

export function classifyTask(task = {}) {
  const type = String(task.type || "").toLowerCase();
  const explicitHuman = Boolean(task.requires_human);
  const requiresHuman = explicitHuman || HUMAN_REQUIRED_TASKS.includes(type);

  return {
    decision: requiresHuman ? "human_required" : "bitey_allowed",
    requires_human: requiresHuman,
    type,
    reason: requiresHuman
      ? "The task requires a real person or explicit human authorization."
      : "The task can be prepared or evaluated by Bitey Trainer, subject to the target platform's rules."
  };
}

export function evaluateResponses({ prompt = "", responses = [] } = {}) {
  const candidates = Array.isArray(responses) ? responses : [];
  const normalized = candidates.map((item, index) => {
    const text = String(item?.text ?? item?.answer ?? item?.content ?? "").trim();
    const words = text ? text.split(/\s+/).length : 0;
    const hasUncertainty = /\b(no sé|no estoy seguro|uncertain|cannot verify|can't verify)\b/i.test(text);
    const hasUsefulStructure = /(^|\n)([-*•]|\d+[.)])\s+/.test(text);
    const score = Math.max(0, Math.min(1,
      (text ? 0.35 : 0) +
      Math.min(words / 180, 0.25) +
      (hasUsefulStructure ? 0.15 : 0) +
      (hasUncertainty ? 0.05 : 0.10) +
      Math.min(String(item?.source || "").length / 40, 0.10)
    ));

    return {
      index,
      source: item?.source || `candidate-${index + 1}`,
      score: Number(score.toFixed(3)),
      usable: Boolean(text),
      text
    };
  }).sort((a, b) => b.score - a.score);

  return {
    trainer_version: TRAINER_VERSION,
    prompt: String(prompt),
    candidates: normalized,
    best_candidate: normalized[0] || null,
    validation_required: true,
    note: "Scores are heuristic. A high score is not proof of factual correctness."
  };
}

export function buildTrainingPlan({ objective, audience, currentProblems = [] } = {}) {
  return {
    trainer_version: TRAINER_VERSION,
    objective: String(objective || "Improve the target AI's quality and consistency."),
    audience: String(audience || "business").toLowerCase(),
    phases: [
      { id: "diagnose", title: "Diagnóstico", actions: ["collect_examples", "identify_failure_patterns"] },
      { id: "knowledge", title: "Conocimiento", actions: ["organize_authorized_sources", "create_ground_truth_examples"] },
      { id: "evaluate", title: "Evaluación", actions: ["compare_outputs", "run_regression_tests"] },
      { id: "improve", title: "Mejora", actions: ["refine_instructions", "adjust_routing", "propose_dataset_changes"] },
      { id: "verify", title: "Verificación", actions: ["human_review_when_required", "approve_changes_before_production"] }
    ],
    current_problems: Array.isArray(currentProblems) ? currentProblems : [],
    automatic_promotion: false
  };
}

export function buildOpportunityAlert(opportunity = {}) {
  const classification = classifyTask(opportunity);
  return {
    title: String(opportunity.title || "Oportunidad de entrenamiento de IA"),
    source: opportunity.source || null,
    compensation: opportunity.compensation || null,
    classification,
    action: classification.requires_human
      ? "notify_owner_for_approval"
      : "prepare_for_review",
    automatic_application: false
  };
}
