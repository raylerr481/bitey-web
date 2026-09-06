from __future__ import annotations

"""Native Bitey Skills Engine.

A Skill is a versioned capability contract, not a provider prompt. Skills can be
created from a goal, validated locally, versioned, and selected by domain. The
engine deliberately has no Skywork dependency and no paid-service dependency.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any


_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SkillSpec:
    name: str
    version: str
    description: str
    domain: str
    objective: str
    capabilities: tuple[str, ...] = ()
    workflow: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    cost_class: str = "free"
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "domain": self.domain,
            "objective": self.objective,
            "capabilities": list(self.capabilities),
            "workflow": list(self.workflow),
            "tools": list(self.tools),
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "cost_class": self.cost_class,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SkillValidation:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": list(self.errors), "warnings": list(self.warnings)}


class SkillEngine:
    """Registry and validator for Bitey's independently owned skills."""

    VERSION = "1.0"
    FORBIDDEN_PROVIDER_TERMS = ("skywork",)
    ALLOWED_COST_CLASSES = {"free", "paid", "unknown"}

    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}

    @staticmethod
    def slugify(value: str) -> str:
        value = _SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")
        return value or "skill"

    def validate(self, skill: SkillSpec) -> SkillValidation:
        errors: list[str] = []
        warnings: list[str] = []
        if not skill.name.strip(): errors.append("name_required")
        if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", skill.version): errors.append("invalid_version")
        if not skill.objective.strip(): errors.append("objective_required")
        if not skill.domain.strip(): errors.append("domain_required")
        if not skill.workflow: errors.append("workflow_required")
        if not skill.success_criteria: errors.append("success_criteria_required")
        if skill.cost_class not in self.ALLOWED_COST_CLASSES: errors.append("invalid_cost_class")
        haystack = " ".join((skill.name, skill.description, skill.objective, *skill.capabilities, *skill.workflow, *skill.tools)).lower()
        if any(term in haystack for term in self.FORBIDDEN_PROVIDER_TERMS): errors.append("forbidden_external_dependency")
        if skill.cost_class != "free": warnings.append("skill_not_free_by_default")
        if not skill.constraints: warnings.append("constraints_not_defined")
        return SkillValidation(not errors, tuple(errors), tuple(warnings))

    def register(self, skill: SkillSpec) -> SkillValidation:
        validation = self.validate(skill)
        if validation.valid:
            self._skills[skill.name] = skill
        return validation

    def create_from_goal(
        self,
        goal: str,
        *,
        domain: str = "general",
        name: str | None = None,
        capabilities: tuple[str, ...] = (),
        tools: tuple[str, ...] = (),
    ) -> SkillSpec:
        clean_goal = " ".join(str(goal or "").split())
        skill_name = name or f"skill-{self.slugify(clean_goal)[:48]}"
        workflow = (
            "understand_goal",
            "collect_relevant_context",
            "plan_solution",
            "execute_allowed_capabilities",
            "verify_result",
            "learn_from_feedback",
        )
        criteria = ("answer_or_artifact_is_complete", "result_is_verified", "no_forbidden_cost_is_introduced")
        constraints = (
            "use_only_declared_capabilities",
            "free_only_by_default",
            "do_not_execute_high_impact_actions_without_authorization",
        )
        return SkillSpec(
            name=skill_name,
            version="1.0.0",
            description=f"Bitey skill for: {clean_goal}",
            domain=domain,
            objective=clean_goal,
            capabilities=capabilities,
            workflow=workflow,
            tools=tools,
            success_criteria=criteria,
            constraints=constraints,
            cost_class="free",
            metadata={"created_by": "bitey-native-skill-engine", "created_at": datetime.now(timezone.utc).isoformat()},
        )

    def resolve(self, domain: str, capabilities: set[str] | None = None) -> list[SkillSpec]:
        requested = {str(x).lower() for x in (capabilities or set())}
        matches: list[SkillSpec] = []
        for skill in self._skills.values():
            if not skill.enabled or skill.cost_class != "free":
                continue
            if skill.domain.lower() == domain.lower() or requested.intersection({x.lower() for x in skill.capabilities}):
                matches.append(skill)
        return sorted(matches, key=lambda s: (s.domain.lower() != domain.lower(), s.name))

    def available(self) -> list[dict[str, Any]]:
        return [skill.as_dict() for skill in sorted(self._skills.values(), key=lambda s: s.name)]

    def status(self) -> dict[str, Any]:
        return {
            "engine": "bitey-native-skill-engine",
            "version": self.VERSION,
            "skills": len(self._skills),
            "free_only_default": True,
            "external_provider_dependency": False,
            "skywork_dependency": False,
        }
