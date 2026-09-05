from app.workspace_api import architecture_components


def test_architecture_manifest_is_zero_cost_and_bitey_owned():
    result = __import__('asyncio').run(architecture_components())
    assert result['policy'] == 'zero_cost'
    assert result['decision_owner'] == 'bitey_ia'
    assert result['paid_fallback'] is False
    assert result['vendor_lock_in'] is False
    assert result['all_allowed'] is True
    assert result['components']
