from app.core.context_selector import essential_coverage, select_context


def test_general_excludes_specialized_capability_records():
    source = {
        "user_query": "Necesito una explicación sobre ventas",
        "current_message": "¿Qué significa CRM?",
        "execution_context": {"capability": "general"},
        "memory": [
            {"capability": "general", "text": "CRM significa gestión de relaciones con clientes."},
            {"capability": "enterprise", "text": "Campaña de marketing activa y leads."},
            {"capability": "sbt", "text": "Señal EUR/USD y backtest."},
            {"capability": "jobia", "text": "CV y vacantes remotas."},
        ],
        "enterprise_context": {"company": "Acme", "strategy": "marketing"},
    }

    selected, diagnostics = select_context(source)

    assert diagnostics["capability"] == "general"
    assert selected["memory"] == [
        {"capability": "general", "text": "CRM significa gestión de relaciones con clientes."}
    ]
    assert "enterprise_context" not in selected


def test_enterprise_keeps_enterprise_and_removes_other_specialized_records():
    source = {
        "user_query": "Diseña una campaña para captar clientes",
        "execution_context": {"capability": "enterprise"},
        "memory": [
            {"capability": "enterprise", "text": "Historial de campañas y leads."},
            {"capability": "sbt", "text": "Historial de trading."},
            {"capability": "jobia", "text": "Historial de candidaturas."},
            {"text": "Preferencia general del usuario."},
        ],
        "enterprise_context": {"company": "Acme", "strategy": "lead generation"},
    }

    selected, diagnostics = select_context(source)

    assert diagnostics["capability"] == "enterprise"
    assert selected["memory"] == [
        {"capability": "enterprise", "text": "Historial de campañas y leads."},
        {"text": "Preferencia general del usuario."},
    ]
    assert selected["enterprise_context"] == {"company": "Acme", "strategy": "lead generation"}


def test_nested_capability_records_are_filtered():
    source = {
        "user_query": "Resume mi contexto",
        "execution_context": {"capability": "jobia"},
        "learned_cognitive_context": {
            "general": "Preferencias generales",
            "jobia": {"capability": "jobia", "profile": "Python"},
            "sbt": {"capability": "sbt", "strategy": "EMA"},
        },
    }

    selected, _ = select_context(source)

    assert "sbt" not in selected["learned_cognitive_context"]
    assert selected["learned_cognitive_context"]["jobia"] == {
        "capability": "jobia",
        "profile": "Python",
    }
    assert selected["learned_cognitive_context"]["general"] == "Preferencias generales"


def test_explicit_function_capability_overrides_client_source_capability():
    source = {
        "capability": "sbt",
        "user_query": "¿Qué es CRM?",
        "enterprise_context": {"company": "Acme"},
        "memory": [{"capability": "enterprise", "text": "Marketing plan"}],
    }

    selected, diagnostics = select_context(source, capability="general")

    assert diagnostics["capability"] == "general"
    assert "enterprise_context" not in selected
    assert selected.get("user_query") == "¿Qué es CRM?"
    assert selected.get("memory") == []


def test_essential_context_remains_preserved():
    source = {
        "user_query": "¿Qué es SEO?",
        "current_message": "Explícame SEO",
        "goals": "Entender el concepto",
        "constraints": "Respuesta breve",
        "execution_context": {"capability": "general"},
        "sbt_context": {"strategy": "trading"},
    }

    selected, _ = select_context(source)
    coverage = essential_coverage(selected, source)

    assert coverage["ok"] is True
    assert coverage["missing"] == []
