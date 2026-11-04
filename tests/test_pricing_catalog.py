import pytest

from api.core.pricing_catalog import (
    CatalogPrice,
    validate_pricing_catalog,
)


def price(
    *,
    plan_code="pastor_pro",
    market_code="GH",
    currency="GHS",
    billing_interval="monthly",
    amount_minor=10000,
):
    return CatalogPrice(
        plan_code=plan_code,
        market_code=market_code,
        currency=currency,
        billing_interval=billing_interval,
        amount_minor=amount_minor,
    )


def test_valid_catalog_is_normalized():
    result = validate_pricing_catalog(
        [
            price(
                plan_code=" pastor_pro ",
                market_code=" gh ",
                currency=" ghs ",
                billing_interval=" MONTHLY ",
            )
        ]
    )

    assert result == (
        CatalogPrice(
            plan_code="pastor_pro",
            market_code="GH",
            currency="GHS",
            billing_interval="monthly",
            amount_minor=10000,
        ),
    )


def test_all_commercial_plans_are_allowed():
    result = validate_pricing_catalog(
        [
            price(plan_code="pastor_pro"),
            price(
                plan_code="church",
                market_code="US",
                currency="USD",
            ),
            price(
                plan_code="church_pro",
                billing_interval="annual",
            ),
        ]
    )

    assert [item.plan_code for item in result] == [
        "pastor_pro",
        "church",
        "church_pro",
    ]


def test_same_plan_can_have_multiple_markets():
    result = validate_pricing_catalog(
        [
            price(market_code="GH", currency="GHS"),
            price(market_code="US", currency="USD"),
        ]
    )

    assert len(result) == 2


def test_same_plan_market_can_have_monthly_and_annual_prices():
    result = validate_pricing_catalog(
        [
            price(billing_interval="monthly"),
            price(billing_interval="annual"),
        ]
    )

    assert len(result) == 2


@pytest.mark.parametrize("plan_code", ["", "   "])
def test_blank_plan_code_rejected(plan_code):
    with pytest.raises(ValueError):
        validate_pricing_catalog([price(plan_code=plan_code)])


def test_unknown_plan_rejected():
    with pytest.raises(ValueError):
        validate_pricing_catalog([price(plan_code="unknown_plan")])


@pytest.mark.parametrize("market_code", ["", "   "])
def test_blank_market_rejected(market_code):
    with pytest.raises(ValueError):
        validate_pricing_catalog([price(market_code=market_code)])


@pytest.mark.parametrize("currency", ["", "US", "USDD", "1SD", "U$D"])
def test_invalid_currency_rejected(currency):
    with pytest.raises(ValueError):
        validate_pricing_catalog([price(currency=currency)])


@pytest.mark.parametrize(
    "billing_interval",
    ["", "weekly", "quarterly"],
)
def test_invalid_billing_interval_rejected(billing_interval):
    with pytest.raises(ValueError):
        validate_pricing_catalog(
            [price(billing_interval=billing_interval)]
        )


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        validate_pricing_catalog([price(amount_minor=-1)])


@pytest.mark.parametrize("amount_minor", [1.5, "1000", True, None])
def test_non_integer_amount_rejected(amount_minor):
    with pytest.raises(ValueError):
        validate_pricing_catalog(
            [price(amount_minor=amount_minor)]
        )


def test_zero_amount_is_structurally_valid():
    result = validate_pricing_catalog(
        [price(amount_minor=0)]
    )

    assert result[0].amount_minor == 0


def test_duplicate_plan_market_interval_rejected_even_if_currency_differs():
    with pytest.raises(ValueError):
        validate_pricing_catalog(
            [
                price(
                    market_code="GH",
                    currency="GHS",
                    billing_interval="monthly",
                ),
                price(
                    market_code="GH",
                    currency="USD",
                    billing_interval="monthly",
                ),
            ]
        )


def test_empty_catalog_is_valid():
    assert validate_pricing_catalog([]) == ()


def test_contract_contains_no_payment_provider_identity():
    fields = set(CatalogPrice.__dataclass_fields__)

    assert fields == {
        "plan_code",
        "market_code",
        "currency",
        "billing_interval",
        "amount_minor",
    }

    assert not any(
        "stripe" in field
        or "provider" in field
        or "paypal" in field
        for field in fields
    )
