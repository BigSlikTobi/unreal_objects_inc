import asyncio
from datetime import timedelta
import json
from pathlib import Path

import pytest

from company_api.models import BotDecisionOutcome, OrderStatus
from company_api.service import (
    CompanySimulationService,
    DEFAULT_ACCELERATION,
    DEFAULT_BANKRUPTCY_BURN_MULTIPLE,
    DEFAULT_DAILY_OVERHEAD_EUR,
    OVERFLOW_PENALTY_EUR,
)
from support_company.models import DisposalOrder, OrderPriority, ServiceWindow, WasteType


def make_order(order_id: str, waste_type: WasteType = WasteType.RECYCLING, quantity_m3: float = 4.0, price: float = 180.0) -> DisposalOrder:
    return DisposalOrder(
        order_id=order_id,
        title="Warehouse recycling pickup",
        customer_request="Please collect a recycling load from our warehouse tomorrow.",
        declared_waste_type=waste_type,
        quantity_m3=quantity_m3,
        offered_price_eur=price,
        priority=OrderPriority.STANDARD,
        service_window=ServiceWindow.NEXT_DAY,
        customer_id="cust-1",
        site_id="site-1",
    )


@pytest.mark.asyncio
async def test_external_bot_claims_order_without_internal_processing():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    first = make_order("order-1")
    await service.ingest_order(first)

    claim = await service.claim_order("order-1", bot_id="bot-alpha")
    orders = await service.get_orders()

    assert claim.status == OrderStatus.CLAIMED.value
    assert orders[0].status == OrderStatus.CLAIMED.value
    assert orders[0].decision_outcome is None
    assert claim.order.order_id == "order-1"
    assert claim.order.baseline_economics is not None
    assert "accept_and_route" in claim.order.action_inputs
    assert claim.order.guardrail_context_base["declared_waste_type"] == first.declared_waste_type.value


@pytest.mark.asyncio
async def test_bot_order_view_hides_internal_execution_metadata():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-2"))

    bot_orders = await service.get_bot_orders()
    assert bot_orders[0].customer_request
    assert not hasattr(bot_orders[0], "action_payload")
    assert not hasattr(bot_orders[0], "decision_summary")
    assert bot_orders[0].baseline_economics is not None
    assert "rent_container" in bot_orders[0].action_inputs
    assert "baseline_margin_eur" in bot_orders[0].guardrail_context_base


@pytest.mark.asyncio
async def test_accept_and_route_updates_revenue_and_container_fill():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    await service.ingest_order(make_order("order-3", waste_type=WasteType.RECYCLING, quantity_m3=2.5, price=210.0))
    await service.claim_order("order-3", bot_id="bot-alpha")
    before_fill = container.fill_level_m3

    result = await service.submit_order_result(
        order_id="order-3",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 2.5},
        decision_summary="Routed the recycling order into existing recycling capacity.",
    )

    assert result.status == OrderStatus.COMPLETED.value
    assert service.invoiced_revenue_eur == 210.0
    assert service.revenue_eur == 0.0
    assert service.accounts_receivable_eur == 210.0
    assert service.containers[container.container_id].fill_level_m3 == pytest.approx(before_fill + 2.5)
    orders = await service.get_orders()
    assert orders[0].projected_action_economics is not None
    assert orders[0].projected_action_economics.projected_action_cost_eur == 0.0
    assert orders[0].projected_action_economics.projected_margin_eur > 0


@pytest.mark.asyncio
async def test_overflow_increments_counter_and_penalty():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    container.fill_level_m3 = container.capacity_m3 - 0.5
    await service.ingest_order(make_order("order-4", waste_type=WasteType.RECYCLING, quantity_m3=2.0, price=120.0))
    await service.claim_order("order-4", bot_id="bot-alpha")

    await service.submit_order_result(
        order_id="order-4",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 2.0},
        decision_summary="Used the only available recycling container.",
    )

    assert service.overflow_count == 1
    assert service.penalty_cost_eur == OVERFLOW_PENALTY_EUR
    assert service.containers[container.container_id].overflowed is True


@pytest.mark.asyncio
async def test_bankruptcy_restarts_company_and_keeps_counter():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    before = await service.get_status()
    service.cash_balance_eur = service._bankruptcy_threshold_eur() - 50.0

    status = await service.get_status()
    assert service.bankruptcy_count == 1
    assert status.current_run_id == 2
    assert status.stats.total_orders == 0
    assert status.current_run_started_at is not None
    assert status.current_run_started_at != before.current_run_started_at


@pytest.mark.asyncio
async def test_bankruptcy_threshold_tracks_baseline_cycle_cost():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()

    assert service._baseline_cycle_cost_eur() == 0.0
    assert service._daily_burn_eur() == DEFAULT_DAILY_OVERHEAD_EUR
    assert service._bankruptcy_threshold_eur() == -DEFAULT_BANKRUPTCY_BURN_MULTIPLE * DEFAULT_DAILY_OVERHEAD_EUR


@pytest.mark.asyncio
async def test_default_snapshot_starts_with_at_least_thirty_days_of_runway():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()

    runway_days = (service.cash_balance_eur - service._bankruptcy_threshold_eur()) / service._daily_burn_eur()

    assert runway_days >= 30


@pytest.mark.asyncio
async def test_scheduled_emptying_records_pickup_exchange_cost_only_for_non_empty_containers():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()

    non_empty = next(container for container in service.containers.values() if container.fill_level_m3 > 0.05)
    empty = next(container for container in service.containers.values() if container.container_id != non_empty.container_id)
    empty.fill_level_m3 = 0.0

    expected_cost = non_empty.rental_cost_per_cycle_eur
    non_empty.next_empty_at = service._virtual_now() - timedelta(hours=1)
    empty.next_empty_at = service._virtual_now() - timedelta(hours=1)

    await service.get_status()

    assert service.rental_cost_eur == expected_cost
    assert any(payable.category == "pickup_exchange" and payable.amount_eur == expected_cost for payable in service.payables)


@pytest.mark.asyncio
async def test_service_start_generates_orders_in_continuous_mode():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=None,
        generator_mode="template",
    )
    await service.initialize()
    initial_total = len(await service.get_orders())
    service._next_generation_delay_seconds = lambda: 0.05

    await service.start()
    await asyncio.sleep(0.2)
    await service.stop()

    later_total = len(await service.get_orders())
    assert later_total > initial_total


@pytest.mark.asyncio
async def test_bounded_rolling_mode_seeds_small_bootstrap_and_then_trickles_orders():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=5,
        rolling_generation=True,
        generator_mode="template",
    )
    await service.initialize()
    initial_total = len(await service.get_orders())

    assert initial_total == 2
    service._next_generation_delay_seconds = lambda: 0.05

    await service.start()
    await asyncio.sleep(0.2)
    await service.stop()

    later_total = len(await service.get_orders())
    assert later_total > initial_total
    assert later_total <= 5


def test_generation_delay_stays_within_stress_window():
    from company_api.service import DEFAULT_ORDER_INTERVAL_REAL_SECONDS
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0, seed=42)

    samples = [service._next_generation_delay_seconds() for _ in range(20)]

    assert all(
        (DEFAULT_ORDER_INTERVAL_REAL_SECONDS * 0.75) <= sample <= (DEFAULT_ORDER_INTERVAL_REAL_SECONDS * 1.25)
        for sample in samples
    )


@pytest.mark.asyncio
async def test_completed_order_creates_receivable_before_cash_collection():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    starting_cash = service.cash_balance_eur
    await service.ingest_order(make_order("order-cash", waste_type=WasteType.RECYCLING, quantity_m3=2.0, price=220.0))
    await service.claim_order("order-cash", bot_id="bot-alpha")

    await service.submit_order_result(
        order_id="order-cash",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 2.0},
        decision_summary="Routed with invoice-based settlement.",
    )

    economics = await service.get_economics()
    assert economics.invoiced_revenue_eur == 220.0
    assert economics.revenue_eur == 0.0
    assert economics.accounts_receivable_eur == 220.0
    assert economics.cash_balance_eur <= starting_cash


@pytest.mark.asyncio
async def test_cash_is_collected_after_payment_delay():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    await service.ingest_order(make_order("order-delay", waste_type=WasteType.RECYCLING, quantity_m3=1.0, price=120.0))
    await service.claim_order("order-delay", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-delay",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 1.0},
        decision_summary="Routed with delayed payment.",
    )

    service._real_start -= timedelta(hours=73 / service.acceleration)
    economics = await service.get_economics()

    assert economics.revenue_eur == 120.0
    assert economics.accounts_receivable_eur == 0.0


@pytest.mark.asyncio
async def test_pricing_catalog_exposes_market_quotes_and_operational_options():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()

    pricing = await service.get_pricing(waste_type=WasteType.PAPER.value)

    assert pricing.currency == "EUR"
    assert pricing.market_quotes
    assert all(option.waste_type == WasteType.PAPER.value for option in pricing.market_quotes)
    assert pricing.operational_options
    assert all(option.waste_type in {WasteType.PAPER.value, "all"} for option in pricing.operational_options)


@pytest.mark.asyncio
async def test_custom_cost_policy_flows_into_pricing_and_economics(tmp_path):
    policy_path = tmp_path / "cost-policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "starting_cash_eur": 12_345.0,
                "daily_overhead_eur": 432.0,
                "bankruptcy_burn_multiple": 7.0,
                "overflow_penalty_eur": 222.0,
                "customer_payment_delay_hours": {
                    "same_day": 12,
                    "next_day": 24,
                    "scheduled": 36,
                },
            }
        )
    )
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        cost_policy_path=policy_path,
    )
    await service.initialize()

    pricing = await service.get_pricing()
    economics = await service.get_economics()

    assert pricing.policy["starting_cash_eur"] == 12_345.0
    assert pricing.policy["daily_overhead_eur"] == 432.0
    assert pricing.policy["overflow_penalty_eur"] == 222.0
    assert pricing.policy["customer_payment_delay_hours"]["next_day"] == 24
    assert economics.cash_balance_eur == 12_345.0
    assert economics.daily_burn_eur == 432.0
    assert economics.bankruptcy_threshold_eur == -3_024.0
    assert economics.net_working_capital_eur == 12_345.0
    assert economics.approval_locked_order_count == 0
    assert economics.approval_locked_revenue_eur == 0.0


def test_cost_policy_partial_mapping_overrides_preserve_defaults(tmp_path):
    policy_path = tmp_path / "cost-policy-partial.json"
    policy_path.write_text(
        json.dumps(
            {
                "quote_margin_multiplier": {
                    WasteType.PAPER.value: 1.5,
                },
                "customer_payment_delay_hours": {
                    ServiceWindow.NEXT_DAY.value: 12,
                },
                "hazardous_vendor_payment_delay_hours": 18,
            }
        )
    )

    from support_company.cost_policy import load_cost_policy

    policy = load_cost_policy(policy_path)

    assert policy.quote_margin_multiplier[WasteType.PAPER.value] == 1.5
    assert policy.quote_margin_multiplier[WasteType.RECYCLING.value] > 0
    assert policy.customer_payment_delay_hours[ServiceWindow.NEXT_DAY.value] == 12
    assert policy.customer_payment_delay_hours[ServiceWindow.SAME_DAY.value] > 0
    assert policy.hazardous_vendor_payment_delay_hours == 18


def test_hazardous_vendor_payment_delay_comes_from_policy(tmp_path):
    policy_path = tmp_path / "cost-policy-hazmat-delay.json"
    policy_path.write_text(json.dumps({"hazardous_vendor_payment_delay_hours": 30}))

    from support_company.cost_policy import estimate_vendor_payment_delay_hours, load_cost_policy

    policy = load_cost_policy(policy_path)

    assert (
        estimate_vendor_payment_delay_hours(
            policy=policy,
            service_window=ServiceWindow.SAME_DAY,
            hazardous_flag=True,
        )
        == 30
    )


@pytest.mark.asyncio
async def test_order_views_expose_baseline_context_and_server_side_projection():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    await service.ingest_order(make_order("order-proj", waste_type=WasteType.RECYCLING, quantity_m3=1.5, price=180.0))
    await service.claim_order("order-proj", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-proj",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="rent_container",
        action_payload={
            "target_waste_type": WasteType.RECYCLING.value,
            "target_container_id": container.container_id,
            "route_quantity_m3": 1.5,
            "added_capacity_m3": 8.0,
            "extra_rental_cost_eur": 125.0,
            "early_empty_cost_eur": 110.0,
            "projected_margin_eur": -9999.0,
        },
        decision_summary="Need external decision with projected economics.",
        request_id="req-proj",
    )

    orders = await service.get_orders()
    approvals = await service.get_approvals()

    assert orders[0].baseline_economics is not None
    assert orders[0].guardrail_context_base["current_cash_balance_eur"] == round(service.cash_balance_eur, 2)
    assert orders[0].projected_action_economics is not None
    assert orders[0].projected_action_economics.projected_action_cost_eur == 156.25
    assert orders[0].projected_action_economics.cost_policy_version == service.cost_policy.version
    assert approvals[0].baseline_economics is not None
    assert approvals[0].projected_action_economics is not None


@pytest.mark.asyncio
async def test_live_rule_group_refreshes_rules_from_unreal_objects(monkeypatch):
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        rule_group_id="grp-live",
    )

    async def fake_fetch(group_id: str) -> dict:
        assert group_id == "grp-live"
        return {
            "id": "grp-live",
            "name": "Live Rules",
            "description": "",
            "rules": [
                {
                    "id": "rule-live-1",
                    "name": "Live Capacity Rule",
                    "feature": "capacity",
                    "active": True,
                    "datapoints": ["available_capacity_m3"],
                    "edge_cases": [],
                    "edge_cases_json": [],
                    "rule_logic": "IF available_capacity_m3 < 1 THEN REJECT",
                    "rule_logic_json": {"if": [{ "<": [{"var": "available_capacity_m3"}, 1]}, "REJECT", None]},
                }
            ],
        }

    monkeypatch.setattr(service, "_fetch_live_rule_group", fake_fetch)

    async def fake_groups() -> list[dict]:
        return [await fake_fetch("grp-live")]

    monkeypatch.setattr(service, "_fetch_live_rule_groups", fake_groups)

    await service.initialize()

    assert service.group_id == "grp-live"
    assert len(service.rules) == 1
    assert service.rules[0].name == "Live Capacity Rule"


@pytest.mark.asyncio
async def test_live_rule_catalog_lists_all_groups_without_pinned_group(monkeypatch):
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
    )

    async def fake_groups() -> list[dict]:
        return [
            {
                "id": "grp-one",
                "name": "Operations",
                "description": "",
                "rules": [
                    {
                        "id": "rule-1",
                        "name": "Capacity Guard",
                        "feature": "capacity",
                        "active": True,
                        "datapoints": ["available_capacity_m3"],
                        "edge_cases": [],
                        "edge_cases_json": [],
                        "rule_logic": "IF available_capacity_m3 < 1 THEN REJECT",
                        "rule_logic_json": {"if": [{ "<": [{"var": "available_capacity_m3"}, 1]}, "REJECT", None]},
                    }
                ],
            },
            {
                "id": "grp-two",
                "name": "Economics",
                "description": "",
                "rules": [
                    {
                        "id": "rule-2",
                        "name": "Loss Guard",
                        "feature": "economics",
                        "active": True,
                        "datapoints": ["offered_price_eur"],
                        "edge_cases": [],
                        "edge_cases_json": [],
                        "rule_logic": "IF offered_price_eur < 10 THEN REJECT",
                        "rule_logic_json": {"if": [{ "<": [{"var": "offered_price_eur"}, 10]}, "REJECT", None]},
                    }
                ],
            },
        ]

    monkeypatch.setattr(service, "_fetch_live_rule_groups", fake_groups)

    await service.initialize()

    assert service.group_id is None
    assert {group.id for group in service.rule_groups} == {"grp-one", "grp-two"}
    assert {rule.group_name for rule in service.rules} == {"Operations", "Economics"}


@pytest.mark.asyncio
async def test_hosted_mode_status_exposes_capabilities():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        deployment_mode="hosted",
        public_voting_enabled=True,
        operator_auth_enabled=True,
        persistence_path="tmp/company-state.json",
    )
    await service.initialize()

    status = await service.get_status()

    assert status.deployment_mode == "hosted"
    assert status.public_voting_enabled is True
    assert status.operator_auth_enabled is True
    assert status.persistence_backend == "json"


@pytest.mark.asyncio
async def test_local_mode_enables_public_voting_by_default():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        deployment_mode="local",
    )
    await service.initialize()

    status = await service.get_status()

    assert status.public_voting_enabled is True


@pytest.mark.asyncio
async def test_public_vote_records_counts():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-6"))
    await service.claim_order("order-6", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-6",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="schedule_early_empty",
        action_payload={"target_container_id": next(iter(service.containers.values())).container_id, "route_quantity_m3": 1.0},
        decision_summary="Need approval before scheduling an early empty.",
        request_id="req-6",
    )

    item = await service.record_public_vote("req-6", approved=True)

    assert item.vote_summary.approve_votes == 1
    assert item.vote_summary.reject_votes == 0


@pytest.mark.asyncio
async def test_finalize_approval_approved_routes_order(monkeypatch):
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    await service.ingest_order(make_order("order-7", waste_type=WasteType.RECYCLING, quantity_m3=1.5, price=150.0))
    await service.claim_order("order-7", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-7",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 1.5},
        decision_summary="Need approval before routing this load.",
        request_id="req-7",
    )

    async def fake_submit(request_id: str, approved: bool, approver: str) -> None:
        assert request_id == "req-7"
        assert approved is True
        assert approver == "alice"

    monkeypatch.setattr(service, "_submit_unreal_objects_approval", fake_submit)

    result = await service.finalize_approval("req-7", approved=True, reviewer="alice", rationale="Looks good.")
    orders = await service.get_orders()

    assert result.final_state == BotDecisionOutcome.APPROVED.value
    assert orders[0].status == OrderStatus.COMPLETED.value
    assert orders[0].decision_outcome == BotDecisionOutcome.APPROVED.value


@pytest.mark.asyncio
async def test_finalize_applies_locally_before_notifying_decision_center(monkeypatch):
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(container for container in service.containers.values() if container.waste_type == WasteType.RECYCLING)
    await service.ingest_order(make_order("order-7b", waste_type=WasteType.RECYCLING, quantity_m3=1.5, price=150.0))
    await service.claim_order("order-7b", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-7b",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="accept_and_route",
        action_payload={"target_container_id": container.container_id, "route_quantity_m3": 1.5},
        decision_summary="Need approval before routing this load.",
        request_id="req-7b",
    )

    dc_called = False

    async def failing_submit(request_id: str, approved: bool, approver: str) -> None:
        nonlocal dc_called
        dc_called = True
        raise Exception("Decision Center unavailable")

    monkeypatch.setattr(service, "_submit_unreal_objects_approval", failing_submit)

    result = await service.finalize_approval("req-7b", approved=True, reviewer="alice", rationale="Looks good.")

    # Local state is updated even though DC call failed
    assert result.final_state == BotDecisionOutcome.APPROVED.value
    assert dc_called is True
    approvals = await service.get_approvals()
    assert len(approvals) == 0  # no longer blocked


@pytest.mark.asyncio
async def test_finalize_rejects_gracefully_when_payload_is_empty(monkeypatch):
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-7c", waste_type=WasteType.RECYCLING, quantity_m3=1.5, price=150.0))
    await service.claim_order("order-7c", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-7c",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="accept_and_route",
        action_payload={},  # empty — no target_container_id
        decision_summary="Needs approval.",
        request_id="req-7c",
    )

    async def noop_submit(request_id: str, approved: bool, approver: str) -> None:
        pass

    monkeypatch.setattr(service, "_submit_unreal_objects_approval", noop_submit)

    result = await service.finalize_approval("req-7c", approved=True, reviewer="alice")

    # Should not crash — order rejected gracefully
    orders = await service.get_orders()
    order = next(o for o in orders if o.order_id == "order-7c")
    assert order.status == "rejected"
    assert "did not specify a target container" in order.resolution


@pytest.mark.asyncio
async def test_persistence_restores_runtime_state(tmp_path, monkeypatch):
    persistence_path = tmp_path / "company-state.json"
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        persistence_path=persistence_path,
    )
    await service.initialize()
    await service.ingest_order(make_order("order-8"))
    await service.claim_order("order-8", bot_id="bot-alpha")
    await service.submit_order_result(
        order_id="order-8",
        bot_id="bot-alpha",
        outcome=BotDecisionOutcome.APPROVAL_REQUIRED,
        bot_action="schedule_early_empty",
        action_payload={"target_container_id": next(iter(service.containers.values())).container_id, "route_quantity_m3": 1.0},
        decision_summary="Need approval before early empty.",
        request_id="req-8",
    )
    await service.record_public_vote("req-8", approved=False)

    restored = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        persistence_path=persistence_path,
    )

    async def no_live_groups() -> list[dict]:
        raise RuntimeError("offline")

    monkeypatch.setattr(restored, "_fetch_live_rule_groups", no_live_groups)

    await restored.initialize()
    approvals = await restored.get_approvals()

    assert approvals[0].request_id == "req-8"
    assert approvals[0].vote_summary.reject_votes == 1


@pytest.mark.asyncio
async def test_dynamic_early_empty_cost_varies_with_fill_ratio():
    from support_company.cost_policy import compute_dynamic_early_empty_cost
    low_fill = compute_dynamic_early_empty_cost(
        base_cost=100.0, fill_ratio=0.2, hours_to_pickup=24.0, overflow_penalty_eur=350.0,
    )
    high_fill = compute_dynamic_early_empty_cost(
        base_cost=100.0, fill_ratio=0.8, hours_to_pickup=24.0, overflow_penalty_eur=350.0,
    )
    assert high_fill < low_fill, "Higher fill ratio should yield lower (discounted) cost"


@pytest.mark.asyncio
async def test_dynamic_cost_cheaper_near_overflow():
    from support_company.cost_policy import compute_dynamic_early_empty_cost
    at_90 = compute_dynamic_early_empty_cost(
        base_cost=100.0, fill_ratio=0.92, hours_to_pickup=24.0, overflow_penalty_eur=350.0,
    )
    at_50 = compute_dynamic_early_empty_cost(
        base_cost=100.0, fill_ratio=0.5, hours_to_pickup=24.0, overflow_penalty_eur=350.0,
    )
    assert at_90 < at_50 * 0.5, "Near-overflow cost should be heavily discounted"


@pytest.mark.asyncio
async def test_standalone_early_empty_resets_container():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(c for c in service.containers.values() if c.waste_type == WasteType.RECYCLING)
    container.fill_level_m3 = container.capacity_m3 * 0.8

    result = await service.early_empty_container(container.container_id, bot_id="bot-alpha")

    assert container.fill_level_m3 == 0.0
    assert service.overflow_prevented_count == 1
    assert service.overflow_penalty_avoided_eur == OVERFLOW_PENALTY_EUR
    assert service.proactive_early_empty_cost_eur > 0
    assert result["fill_level_m3"] == 0.0
    assert len([p for p in service.payables if p.category == "proactive_early_empty"]) == 1


@pytest.mark.asyncio
async def test_standalone_early_empty_on_empty_container_rejected():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(c for c in service.containers.values() if c.waste_type == WasteType.RECYCLING)
    container.fill_level_m3 = 0.0

    with pytest.raises(ValueError, match="already empty"):
        await service.early_empty_container(container.container_id, bot_id="bot-alpha")


@pytest.mark.asyncio
async def test_economics_tracks_avoided_penalties():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(c for c in service.containers.values() if c.waste_type == WasteType.RECYCLING)
    container.fill_level_m3 = container.capacity_m3 * 0.85

    await service.early_empty_container(container.container_id, bot_id="bot-alpha")
    economics = await service.get_economics()

    assert economics.overflow_prevented_count == 1
    assert economics.overflow_penalty_avoided_eur == OVERFLOW_PENALTY_EUR
    assert economics.proactive_early_empty_cost_eur > 0


@pytest.mark.asyncio
async def test_bankruptcy_reset_clears_prevention_counters():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    container = next(c for c in service.containers.values() if c.waste_type == WasteType.RECYCLING)
    container.fill_level_m3 = container.capacity_m3 * 0.9
    await service.early_empty_container(container.container_id, bot_id="bot-alpha")
    assert service.overflow_prevented_count == 1

    # Force bankruptcy
    service.cash_balance_eur = service._bankruptcy_threshold_eur() - 50.0
    await service.get_status()

    assert service.overflow_prevented_count == 0
    assert service.overflow_penalty_avoided_eur == 0.0
    assert service.proactive_early_empty_cost_eur == 0.0


@pytest.mark.asyncio
async def test_release_order_returns_to_open():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-release"))
    await service.claim_order("order-release", bot_id="bot-alpha")

    result = await service.release_order("order-release", bot_id="bot-alpha")

    assert result["released"] is True
    assert result["status"] == OrderStatus.OPEN.value
    orders = await service.get_orders()
    assert orders[0].status == OrderStatus.OPEN.value
    assert orders[0].assigned_to is None


@pytest.mark.asyncio
async def test_release_order_rejects_wrong_bot():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-release-wrong"))
    await service.claim_order("order-release-wrong", bot_id="bot-alpha")

    with pytest.raises(ValueError, match="not assigned to"):
        await service.release_order("order-release-wrong", bot_id="bot-beta")


@pytest.mark.asyncio
async def test_release_order_rejects_non_claimed():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-release-open"))

    with pytest.raises(ValueError, match="not claimed"):
        await service.release_order("order-release-open", bot_id="bot-alpha")


@pytest.mark.asyncio
async def test_claim_expiry_releases_stale_claims():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        bot_connection_timeout_seconds=1,
    )
    await service.initialize()
    await service.ingest_order(make_order("order-expire"))
    await service.claim_order("order-expire", bot_id="bot-alpha")

    assert (await service.get_orders())[0].status == OrderStatus.CLAIMED.value

    # Simulate time passing beyond the expiry threshold
    from company_api.service import utcnow
    service.claimed_at["order-expire"] = utcnow() - timedelta(seconds=2)

    # Trigger maintenance expiry
    service._expire_stale_claims_locked()

    orders = await service.get_orders()
    assert orders[0].status == OrderStatus.OPEN.value
    assert orders[0].assigned_to is None
    assert "order-expire" not in service.claimed_at


@pytest.mark.asyncio
async def test_claim_expiry_does_not_release_fresh_claims():
    service = CompanySimulationService(
        rule_pack_path=Path("rule_packs/support_company.json"),
        initial_order_count=0,
        bot_connection_timeout_seconds=120,
    )
    await service.initialize()
    await service.ingest_order(make_order("order-fresh"))
    await service.claim_order("order-fresh", bot_id="bot-alpha")

    service._expire_stale_claims_locked()

    orders = await service.get_orders()
    assert orders[0].status == OrderStatus.CLAIMED.value


@pytest.mark.asyncio
async def test_released_order_can_be_reclaimed():
    service = CompanySimulationService(rule_pack_path=Path("rule_packs/support_company.json"), initial_order_count=0)
    await service.initialize()
    await service.ingest_order(make_order("order-reclaim"))
    await service.claim_order("order-reclaim", bot_id="bot-alpha")
    await service.release_order("order-reclaim", bot_id="bot-alpha")

    claim = await service.claim_order("order-reclaim", bot_id="bot-beta")

    assert claim.status == OrderStatus.CLAIMED.value
    assert claim.assigned_to == "bot-beta"
