from __future__ import annotations

import hashlib
import math
import os
from collections import defaultdict
from typing import Any

import httpx


class BiteyQLearning:
    """Small, dependency-free tabular Q-learning policy for Bitey's routing.

    It learns which already-allowed action/tool is most useful for a state.
    It never bypasses evidence, safety, risk, or the executive brain.
    Persistence is optional and uses the existing Supabase learning table.
    Without Supabase it still works in-process at zero cost.
    """

    VERSION = "q-routing-v2-global"
    DEFAULT_ACTION = "DIRECT_ANSWER"

    def __init__(self) -> None:
        self.enabled = os.getenv("BITEY_QLEARNING_ENABLED", "true").lower() != "false"
        self.alpha = max(0.01, min(1.0, float(os.getenv("BITEY_Q_ALPHA", "0.20"))))
        self.gamma = max(0.0, min(0.99, float(os.getenv("BITEY_Q_GAMMA", "0.90"))))
        self.epsilon = max(0.0, min(0.25, float(os.getenv("BITEY_Q_EPSILON", "0.05"))))
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self._q: dict[str, dict[str, float]] = defaultdict(dict)
        self._samples: dict[tuple[str, str], int] = defaultdict(int)
        self._transitions = 0
        self._last: dict[str, dict[str, Any]] = {}
        self._hydrated = False

    async def hydrate(self) -> dict[str, Any]:
        """Load persisted Q-values once so learning survives API restarts."""
        if self._hydrated:
            return {"hydrated": True, "loaded": 0}
        self._hydrated = True
        if not self.persistent:
            return {"hydrated": True, "loaded": 0, "persistent": False}
        headers = {"apikey": self.key, "Authorization": "Bearer " + self.key}
        loaded = 0
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.url}/rest/v1/cognitive_learning_candidates",
                    headers=headers,
                    params={"candidate_type": "eq.q_learning_policy", "select": "payload", "limit": "5000"},
                )
                response.raise_for_status()
                rows = response.json()
            for row in rows if isinstance(rows, list) else []:
                payload = row.get("payload") if isinstance(row, dict) else None
                if not isinstance(payload, dict):
                    continue
                state = str(payload.get("state") or "")
                action = str(payload.get("action") or "")
                if not state or not action:
                    continue
                self._q.setdefault(state, {})[action] = float(payload.get("q_value") or 0.0)
                self._samples[(state, action)] = max(self._samples[(state, action)], int(payload.get("samples") or 0))
                loaded += 1
            return {"hydrated": True, "loaded": loaded, "persistent": True}
        except Exception:
            return {"hydrated": True, "loaded": 0, "persistent": True, "error": "persistence_read_failed"}

    @property
    def persistent(self) -> bool:
        return bool(self.url and self.key)

    @property
    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "version": self.VERSION,
            "algorithm": "tabular_q_learning",
            "persistent": self.persistent,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "states": len(self._q),
            "learned_pairs": sum(len(v) for v in self._q.values()),
            "transitions": self._transitions,
            "cost_mode": "free_only",
            "safety": "advisory_only; never bypasses executive policy or risk gates",
        }

    def _state(self, context: dict[str, Any]) -> str:
        cognition = context.get("cognition") if isinstance(context.get("cognition"), dict) else {}
        brain = context.get("bitey_brain") if isinstance(context.get("bitey_brain"), dict) else {}
        intent = cognition.get("intention") if isinstance(cognition.get("intention"), dict) else {}
        domain = str(context.get("current_intent_domain") or intent.get("domain") or "general").lower()
        evidence = "1" if bool(brain.get("evidence_required", context.get("evidence_required"))) else "0"
        fresh = "1" if bool(brain.get("freshness_required", context.get("freshness_required"))) else "0"
        continuity = "1" if bool(context.get("conversation_continuity")) else "0"
        prior = context.get("previous_execution_state")
        prior_ok = "1" if isinstance(prior, dict) and prior.get("success") else "0"
        tools = context.get("selected_tools") or []
        tool_sig = ",".join(sorted(str(x) for x in tools)[:8])
        source = str(context.get("source") or context.get("learning_source") or "bitey").lower()
        domain_context = context.get("domain_context")
        if not isinstance(domain_context, dict):
            for candidate in ("sbt", "jobia", "research", "workspace", "automation"):
                if isinstance(context.get(candidate), dict):
                    domain_context = context[candidate]
                    break
        if not isinstance(domain_context, dict):
            domain_context = {}
        safe_context = {
            str(k): str(domain_context[k])[:80]
            for k in sorted(domain_context)
            if str(k) in {
                "task_type", "task_mode", "symbol", "timeframe", "strategy",
                "regime", "signal", "tool_class", "provider_class",
                "workflow", "job_type", "research_type"
            }
        }
        context_sig = hashlib.sha1(
            repr(sorted(safe_context.items())).encode("utf-8")
        ).hexdigest()[:10] if safe_context else "none"
        raw = "|".join((domain, source, evidence, fresh, continuity, prior_ok, tool_sig, context_sig))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]

    def _allowed(self, selected: list[str], context: dict[str, Any]) -> list[str]:
        allowed = [str(x) for x in selected if str(x)]
        if not allowed:
            allowed = [self.DEFAULT_ACTION]
        return list(dict.fromkeys(allowed))

    def state_for(self, context: dict[str, Any]) -> str:
        return self._state(context)

    def normalize_reward(self, reward: float) -> float:
        return max(-1.0, min(1.0, float(reward)))

    def reward_from_outcome(self, *, success: bool | None = None, quality: float | None = None,
                            user_feedback: float | None = None, evidence_quality: float | None = None,
                            tool_success: bool | None = None, penalty: float = 0.0) -> float:
        parts: list[float] = []
        if success is not None:
            parts.append(1.0 if success else -1.0)
        if quality is not None:
            parts.append(self.normalize_reward(quality))
        if user_feedback is not None:
            parts.append(self.normalize_reward(user_feedback))
        if evidence_quality is not None:
            parts.append(self.normalize_reward(evidence_quality))
        if tool_success is not None:
            parts.append(0.5 if tool_success else -0.5)
        reward = sum(parts) / len(parts) if parts else 0.0
        return self.normalize_reward(reward - float(penalty))

    def _scores(self, state: str, actions: list[str]) -> dict[str, float]:
        return {action: float(self._q.get(state, {}).get(action, 0.0)) for action in actions}

    async def choose_async(self, context: dict[str, Any], selected: list[str]) -> dict[str, Any]:
        await self.hydrate()
        return self.choose(context, selected)

    def choose(self, context: dict[str, Any], selected: list[str]) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "selected": list(selected), "action": (selected or [self.DEFAULT_ACTION])[0]}

        actions = self._allowed(selected, context)
        state = self._state(context)
        scores = self._scores(state, actions)
        samples = {a: self._samples[(state, a)] for a in actions}

        # Safe exploration: only reorder tools that the executive brain already
        # approved. Exploration is deterministic when there is no randomness
        # requirement by using the lowest-sampled action.
        explore = any(samples[a] == 0 for a in actions)
        if explore:
            action = min(actions, key=lambda a: (samples[a], -scores[a], a))
            reason = "exploration_unseen"
        else:
            action = max(actions, key=lambda a: (scores[a], samples[a], a))
            reason = "exploitation_q_value"

        decision = {
            "enabled": True,
            "state": state,
            "action": action,
            "selected": actions,
            "q_values": scores,
            "samples": samples,
            "reason": reason,
        }
        self._last[state] = decision
        return decision

    async def learn(
        self,
        context: dict[str, Any],
        *,
        action: str,
        reward: float,
        next_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False}

        await self.hydrate()
        state = self._state(context)
        next_state = self._state(next_context or context)
        action = str(action or self.DEFAULT_ACTION)
        clean_reward = self.normalize_reward(reward)
        current = float(self._q.setdefault(state, {}).get(action, 0.0))
        next_actions = list(self._q.get(next_state, {}).values())
        next_best = max(next_actions) if next_actions else 0.0
        updated = current + self.alpha * (clean_reward + self.gamma * next_best - current)
        self._q[state][action] = round(updated, 6)
        self._samples[(state, action)] += 1
        self._transitions += 1

        if self.persistent:
            await self._persist(state, action, updated, clean_reward)

        return {
            "enabled": True,
            "algorithm": self.VERSION,
            "state": state,
            "next_state": next_state,
            "action": action,
            "reward": clean_reward,
            "q_value": round(updated, 6),
            "samples": self._samples[(state, action)],
            "persistent": self.persistent,
            "safety": "advisory_only",
        }

    def reward_from_evaluation(self, evaluation: dict[str, Any] | None, *, evidence: bool, tool_success: bool) -> float:
        data = evaluation or {}
        decision = str(data.get("decision") or "").lower()
        confidence = max(0.0, min(1.0, float(data.get("confidence") or 0.0)))
        reward = 0.0
        if decision == "accept":
            reward += 0.65 + 0.25 * confidence
        elif decision == "revise":
            reward += 0.15 + 0.10 * confidence
        elif decision == "reject":
            reward -= 0.85
        if evidence:
            reward += 0.10
        if tool_success:
            reward += 0.10
        return max(-1.0, min(1.0, reward))

    async def _persist(self, state: str, action: str, q_value: float, reward: float) -> None:
        row = {
            "candidate_type": "q_learning_policy",
            "title": f"{self.VERSION}:{state}:{action}",
            "payload": {
                "schema_version": self.VERSION,
                "state": state,
                "action": action,
                "q_value": q_value,
                "reward": reward,
                "samples": self._samples[(state, action)],
            },
            "confidence": min(1.0, 0.5 + abs(q_value) * 0.5),
            "source": "bitey_q_learning",
            "evidence_count": self._samples[(state, action)],
            "status": "validated",
        }
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(
                    f"{self.url}/rest/v1/cognitive_learning_candidates",
                    headers=headers,
                    json=row,
                )
        except Exception:
            # Learning must never make a user request fail.
            pass
