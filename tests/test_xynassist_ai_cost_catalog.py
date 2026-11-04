from xynassist_service.core.ai_cost_catalog import (
    APPROVED_AI_COST_CATALOG,
    validate_ai_cost_catalog,
)


def test_approved_catalog_contains_initial_openai_model_rates():
    rates = validate_ai_cost_catalog(
        APPROVED_AI_COST_CATALOG
    )

    by_model = {rate.model: rate for rate in rates}

    assert set(by_model) == {
        "gpt-5.4-mini",
        "gpt-5.4-mini-2026-03-17",
    }

    for rate in by_model.values():
        assert rate.provider == "openai"
        assert rate.input_cost_per_million_micro_usd == 750_000
        assert rate.output_cost_per_million_micro_usd == 4_500_000
