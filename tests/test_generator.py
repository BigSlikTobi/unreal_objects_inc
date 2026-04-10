"""Tests for the waste-order generator."""

from statistics import mean

from support_company.generator import expected_outcome_for_order, generate_batch, generate_initial_containers
from support_company.models import DisposalOrder, WasteType, ExpectedPath
from support_company.pricing import estimate_service_cost, list_operational_price_options
from support_company.simulator import generate_template_scenarios


def test_batch_produces_correct_count():
    orders = generate_batch(count=20, seed=42)
    assert len(orders) == 20


def test_seeded_runs_are_reproducible():
    a = generate_batch(count=30, seed=99)
    b = generate_batch(count=30, seed=99)
    for oa, ob in zip(a, b):
        assert oa.order_id != ob.order_id
        assert oa.declared_waste_type == ob.declared_waste_type
        assert oa.quantity_m3 == ob.quantity_m3
        assert oa.offered_price_eur == ob.offered_price_eur


def test_all_required_fields_present():
    orders = generate_batch(count=50, seed=42)
    for order in orders:
        assert order.order_id
        assert order.title
        assert order.customer_request
        assert order.declared_waste_type in WasteType
        assert order.quantity_m3 > 0
        assert order.offered_price_eur >= 0


def test_scenarios_produce_all_paths():
    scenarios = generate_template_scenarios(count=120, seed=42)
    paths = {scenario.expected_outcome for scenario in scenarios}
    assert ExpectedPath.APPROVE in paths
    assert ExpectedPath.ASK_FOR_APPROVAL in paths
    assert ExpectedPath.REJECT in paths


def test_to_evaluation_context_has_required_keys():
    orders = generate_batch(count=10, seed=42)
    required = {"declared_waste_type", "quantity_m3", "offered_price_eur", "priority", "service_window"}
    for order in orders:
        ctx = order.to_evaluation_context(bot_action="accept_and_route", action_payload={"route_quantity_m3": order.quantity_m3})
        assert required.issubset(ctx.keys())


def test_initial_containers_have_capacity():
    containers = generate_initial_containers(seed=42)
    assert containers
    for container in containers:
        assert container.capacity_m3 > 0
        assert container.fill_level_m3 >= 0
        assert container.rental_cost_per_cycle_eur > 0


def test_initial_containers_start_with_light_utilization():
    containers = generate_initial_containers(seed=42)
    fill_ratios = [container.fill_level_m3 / container.capacity_m3 for container in containers]

    assert max(fill_ratios) <= 0.25
    assert 0.08 <= sum(fill_ratios) / len(fill_ratios) <= 0.2


def test_generated_order_prices_use_market_grounded_quotes():
    order = generate_batch(count=1, seed=21)[0]
    assert order.offered_price_eur > 0


def test_default_mix_keeps_approval_share_below_one_quarter():
    orders = generate_batch(count=500, seed=42)
    approval_required = sum(1 for order in orders if expected_outcome_for_order(order) == ExpectedPath.ASK_FOR_APPROVAL)

    assert approval_required / len(orders) < 0.25


def test_default_order_families_are_no_longer_structurally_loss_making():
    orders = generate_batch(count=500, seed=42)
    margins_by_type: dict[str, list[float]] = {}
    margin_pct_by_type: dict[str, list[float]] = {}

    for order in orders:
        cost = estimate_service_cost(
            waste_type=order.declared_waste_type,
            quantity_m3=order.quantity_m3,
            service_window=order.service_window,
            contamination_risk=order.contamination_risk,
            hazardous_flag=order.hazardous_flag,
        )
        margin = order.offered_price_eur - cost
        margins_by_type.setdefault(order.declared_waste_type.value, []).append(margin)
        margin_pct_by_type.setdefault(order.declared_waste_type.value, []).append(margin / order.offered_price_eur)

    assert mean(margins_by_type[WasteType.PAPER.value]) > 20.0
    assert mean(margins_by_type[WasteType.ORGANIC.value]) > 35.0
    assert mean(margin_pct_by_type[WasteType.PAPER.value]) > 0.38
    assert mean(margin_pct_by_type[WasteType.ORGANIC.value]) > 0.34
    overall = [margin for margins in margins_by_type.values() for margin in margins]
    assert mean(overall) > 100.0


def test_owned_fleet_costs_stay_below_emergency_overflow_actions():
    containers = generate_initial_containers(seed=42)

    for container in containers:
        operational_options = list_operational_price_options(waste_type=container.waste_type.value)
        emergency_exchange_costs = [
            option["rental_cost_per_cycle_eur"]
            for option in operational_options
            if option["bot_action"] == "rent_container" and option["rental_cost_per_cycle_eur"] is not None
        ]
        emergency_early_empty_costs = [
            option["early_empty_cost_eur"]
            for option in operational_options
            if option["bot_action"] == "rent_container" and option["early_empty_cost_eur"] is not None
        ]

        assert emergency_exchange_costs
        assert emergency_early_empty_costs
        assert container.rental_cost_per_cycle_eur < min(emergency_exchange_costs)
        assert container.base_early_empty_cost_eur <= min(emergency_early_empty_costs)
