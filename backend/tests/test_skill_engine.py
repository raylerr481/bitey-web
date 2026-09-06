from app.core.skill_engine import SkillEngine


def test_create_goal_produces_valid_free_skill():
    engine = SkillEngine()
    skill = engine.create_from_goal("analizar contratos", domain="legal", capabilities=("analysis",))
    validation = engine.register(skill)
    assert validation.valid
    assert skill.cost_class == "free"
    assert "verify_result" in skill.workflow
    assert "no_forbidden_cost_is_introduced" in skill.success_criteria


def test_non_free_skill_is_not_resolved():
    engine = SkillEngine()
    skill = engine.create_from_goal("paid capability", domain="general")
    skill = type(skill)(**{**skill.__dict__, "cost_class": "paid"})
    assert engine.register(skill).valid
    assert engine.resolve("general") == []


def test_skywork_dependency_is_rejected():
    engine = SkillEngine()
    skill = engine.create_from_goal("use Skywork capability", domain="general")
    validation = engine.register(skill)
    assert not validation.valid
    assert "forbidden_external_dependency" in validation.errors


def test_skill_status_declares_independence():
    status = SkillEngine().status()
    assert status["free_only_default"] is True
    assert status["external_provider_dependency"] is False
    assert status["skywork_dependency"] is False
