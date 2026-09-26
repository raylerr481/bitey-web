from backend.app.core.cognitive_trace import CognitiveTraceStore


def test_plan_steps_start_pending_and_transition():
    store = CognitiveTraceStore()
    trace = store.start("investiga el mercado actual", "conversation-1", request_id="request-1")
    plan = [
        {"id": "understand", "action": "understand_request", "status": "required"},
        {"id": "retrieve", "action": "retrieve_evidence", "status": "required"},
        {"id": "verify", "action": "verify_claims_and_risk", "status": "required"},
        {"id": "respond", "action": "respond_to_user", "status": "required"},
    ]

    store.set_plan(trace, plan)
    assert all(step["status"] == "pending" for step in trace.decision["plan_steps"])

    store.set_plan_step(trace, "understand", "completed")
    store.set_plan_step(trace, "retrieve", "running")
    snapshot = store.recent(request_id="request-1", limit=1)[0]
    statuses = {step["id"]: step["status"] for step in snapshot["decision"]["plan_steps"]}
    assert statuses["understand"] == "completed"
    assert statuses["retrieve"] == "running"
    assert statuses["verify"] == "pending"


def test_unknown_plan_status_is_normalized():
    store = CognitiveTraceStore()
    trace = store.start("test", "conversation-2")
    store.set_plan(trace, [{"id": "respond", "action": "respond_to_user", "status": "required"}])
    store.set_plan_step(trace, "respond", "something_invalid")
    assert trace.decision["plan_steps"][0]["status"] == "pending"
