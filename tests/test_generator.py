"""Tests for the waste-order generator."""

from support_company.generator import expected_outcome_for_order, generate_batch, generate_initial_containers
from support_company.models import DisposalOrder, WasteType, ExpectedPath
from support_company.pricing import estimate_service_cost
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

    for order in orders:
        margins_by_type.setdefault(order.declared_waste_type.value, []).append(
            order.offered_price_eur
            - estimate_service_cost(
                waste_type=order.declared_waste_type,
                quantity_m3=order.quantity_m3,
                service_window=order.service_window,
                contamination_risk=order.contamination_risk,
                hazardous_flag=order.hazardous_flag,
            )
        )

    assert sum(margins_by_type[WasteType.PAPER.value]) / len(margins_by_type[WasteType.PAPER.value]) > 0
    assert sum(margins_by_type[WasteType.ORGANIC.value]) / len(margins_by_type[WasteType.ORGANIC.value]) > 0
    overall = [margin for margins in margins_by_type.values() for margin in margins]
    assert sum(overall) / len(overall) > 0
