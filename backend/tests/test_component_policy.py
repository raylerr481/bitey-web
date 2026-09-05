from app.core.component_policy import (
    ComponentClass,
    ComponentPolicy,
    validate_core_components,
)


def test_core_component_registry_is_zero_cost():
    validate_core_components()


def test_paid_dependency_is_rejected():
    component = ComponentPolicy(
        "paid-service",
        ComponentClass.OPEN_SOURCE,
        paid_dependency=True,
    )
    assert component.allowed() is False


def test_mandatory_cloud_provider_is_rejected():
    component = ComponentPolicy(
        "external-provider",
        ComponentClass.OPTIONAL_FREE_PROVIDER,
        mandatory=True,
    )
    assert component.allowed() is False


def test_optional_free_provider_can_be_used_without_becoming_core():
    component = ComponentPolicy(
        "free-provider",
        ComponentClass.OPTIONAL_FREE_PROVIDER,
        mandatory=False,
    )
    assert component.allowed() is True


def test_vendor_lock_in_is_rejected():
    component = ComponentPolicy(
        "locked-platform",
        ComponentClass.OPEN_SOURCE,
        vendor_lock_in=True,
    )
    assert component.allowed() is False
