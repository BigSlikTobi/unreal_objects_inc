"""Waste-order and container generators for the simulated company."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import random

from .models import (
    BotActionType,
    CompanyEvent,
    CompanyOperationSnapshot,
    DisposalOrder,
    EventSource,
    EventType,
    ExpectedPath,
    OrderPriority,
    ServiceWindow,
    WasteContainer,
    WasteType,
)
from .pricing import estimate_customer_quote


_ORDER_FAMILIES: list[dict] = [
    {
        "waste_type": WasteType.PAPER,
        "quantity_range": (1.0, 6.0),
        "price_per_m3": (28.0, 42.0),
        "priority": OrderPriority.STANDARD,
        "service_window": ServiceWindow.NEXT_DAY,
        "hazardous_flag": False,
        "contamination_risk": False,
        "expected_action": BotActionType.ACCEPT_AND_ROUTE,
        "expected_outcome": ExpectedPath.APPROVE,
        "title": "Paper pickup for office cleanout",
        "messages": [
            "We need a paper pickup after clearing old files from the office.",
            "Can you collect a load of paper waste from our site tomorrow?",
            "We have stacked paper waste ready for pickup from an office cleanout.",
        ],
    },
    {
        "waste_type": WasteType.RECYCLING,
        "quantity_range": (2.0, 9.0),
        "price_per_m3": (32.0, 48.0),
        "priority": OrderPriority.STANDARD,
        "service_window": ServiceWindow.NEXT_DAY,
        "hazardous_flag": False,
        "contamination_risk": True,
        "expected_action": BotActionType.ACCEPT_AND_ROUTE,
        "expected_outcome": ExpectedPath.APPROVE,
        "title": "Mixed recycling collection",
        "messages": [
            "We need a recycling pickup for packaging waste from our warehouse.",
            "Please collect mixed recycling from our loading area tomorrow.",
            "We have a recycling load ready and need the next available pickup slot.",
        ],
    },
    {
        "waste_type": WasteType.RESIDUAL,
        "quantity_range": (3.0, 11.0),
        "price_per_m3": (40.0, 62.0),
        "priority": OrderPriority.URGENT,
        "service_window": ServiceWindow.SAME_DAY,
        "hazardous_flag": False,
        "contamination_risk": False,
        "expected_action": BotActionType.SCHEDULE_EARLY_EMPTY,
        "expected_outcome": ExpectedPath.ASK_FOR_APPROVAL,
        "title": "Residual waste pickup under pressure",
        "messages": [
            "Our residual waste area is full and we need pickup today.",
            "We need urgent removal of residual waste before the site blocks up.",
            "Residual waste is piling up and we need same-day service if possible.",
        ],
    },
    {
        "waste_type": WasteType.ORGANIC,
        "quantity_range": (2.0, 8.0),
        "price_per_m3": (35.0, 52.0),
        "priority": OrderPriority.STANDARD,
        "service_window": ServiceWindow.SCHEDULED,
        "hazardous_flag": False,
        "contamination_risk": False,
        "expected_action": BotActionType.ACCEPT_AND_ROUTE,
        "expected_outcome": ExpectedPath.APPROVE,
        "title": "Organic waste collection request",
        "messages": [
            "We need regular collection for organic waste from our food operation.",
            "Please schedule pickup for organic waste from our kitchen site.",
            "Our organic waste container is nearly full and we need a scheduled collection.",
        ],
    },
    {
        "waste_type": WasteType.HAZARDOUS,
        "quantity_range": (1.0, 5.0),
        "price_per_m3": (90.0, 150.0),
        "priority": OrderPriority.URGENT,
        "service_window": ServiceWindow.SAME_DAY,
        "hazardous_flag": True,
        "contamination_risk": True,
        "expected_action": BotActionType.RENT_CONTAINER,
        "expected_outcome": ExpectedPath.ASK_FOR_APPROVAL,
        "title": "Hazardous waste handling request",
        "messages": [
            "We need urgent pickup for hazardous waste drums from our workshop.",
            "Can you arrange hazardous waste collection for our site today?",
            "We have hazardous waste that needs controlled pickup as soon as possible.",
        ],
    },
    {
        "waste_type": WasteType.HAZARDOUS,
        "quantity_range": (6.0, 12.0),
        "price_per_m3": (70.0, 95.0),
        "priority": OrderPriority.URGENT,
        "service_window": ServiceWindow.SAME_DAY,
        "hazardous_flag": True,
        "contamination_risk": True,
        "expected_action": BotActionType.REJECT_ORDER,
        "expected_outcome": ExpectedPath.REJECT,
        "title": "Unsupported hazardous load",
        "messages": [
            "We need same-day removal of a large hazardous load from our yard.",
            "Can you collect a hazardous waste load today even though it is larger than usual?",
            "We need immediate removal of hazardous material from a site overflow situation.",
        ],
    },
]


DEFAULT_MIX = [0.2, 0.3, 0.1, 0.22, 0.1, 0.08]


def generate_initial_containers(seed: int = 42, now: datetime | None = None) -> list[WasteContainer]:
    rng = random.Random(seed)
    current = now or datetime.now(UTC)
    templates = [
        ("Residual Bay", WasteType.RESIDUAL, 18.0, 130.0, 160.0, 24),
        ("Recycling Line", WasteType.RECYCLING, 16.0, 120.0, 140.0, 24),
        ("Paper Skip", WasteType.PAPER, 14.0, 85.0, 120.0, 36),
        ("Glass Cage", WasteType.GLASS, 10.0, 95.0, 110.0, 48),
        ("Organic Hopper", WasteType.ORGANIC, 12.0, 110.0, 135.0, 24),
        ("Hazmat Unit", WasteType.HAZARDOUS, 8.0, 190.0, 220.0, 12),
    ]
    containers: list[WasteContainer] = []
    for label, waste_type, capacity, rental, early_empty, interval in templates:
        fill = round(rng.uniform(capacity * 0.06, capacity * 0.24), 2)
        containers.append(
            WasteContainer(
                label=label,
                waste_type=waste_type,
                capacity_m3=capacity,
                fill_level_m3=fill,
                rental_cost_per_cycle_eur=rental,
                early_empty_cost_eur=early_empty,
                emptying_interval_hours=interval,
                last_emptied_at=current - timedelta(hours=rng.randint(3, max(4, interval - 2))),
                next_empty_at=current + timedelta(hours=rng.randint(1, max(2, interval))),
            )
        )
    return containers


def generate_order(rng: random.Random, family: dict) -> DisposalOrder:
    quantity = round(rng.uniform(*family["quantity_range"]), 2)
    offered_price = estimate_customer_quote(
        waste_type=family["waste_type"],
        quantity_m3=quantity,
        service_window=family["service_window"],
        contamination_risk=family["contamination_risk"],
        hazardous_flag=family["hazardous_flag"],
        rng=rng,
    )
    return DisposalOrder(
        title=family["title"],
        customer_request=rng.choice(family["messages"]),
        declared_waste_type=family["waste_type"],
        quantity_m3=quantity,
        offered_price_eur=offered_price,
        priority=family["priority"],
        service_window=family["service_window"],
        customer_id=f"cust-{rng.randint(1000, 9999)}",
        site_id=f"site-{rng.randint(100, 999)}",
        hazardous_flag=family["hazardous_flag"],
        contamination_risk=family["contamination_risk"],
    )


def generate_batch(
    count: int = 50,
    seed: int = 42,
    mix: list[float] | None = None,
) -> list[DisposalOrder]:
    weights = mix or DEFAULT_MIX
    assert len(weights) == len(_ORDER_FAMILIES), "Mix weights must match waste-order family count"

    rng = random.Random(seed)
    return [generate_order(rng, rng.choices(_ORDER_FAMILIES, weights=weights, k=1)[0]) for _ in range(count)]


def generate_order_event(
    order: DisposalOrder,
    operations: CompanyOperationSnapshot,
    occurred_at: datetime,
) -> CompanyEvent:
    note = f"Demand {operations.demand_level}; depot load {operations.depot_load}. {operations.business_note}"
    return CompanyEvent(
        source=EventSource.CUSTOMER,
        event_type=EventType.DISPOSAL_ORDER_REQUEST,
        occurred_at=occurred_at,
        site_id=order.site_id,
        customer_id=order.customer_id,
        summary=f"{order.declared_waste_type.value.title()} disposal order for {order.quantity_m3:.1f} m3.",
        customer_request=order.customer_request,
        internal_notes=note,
    )


def expected_action_for_order(order: DisposalOrder) -> BotActionType:
    if order.hazardous_flag and order.quantity_m3 >= 6:
        return BotActionType.REJECT_ORDER
    if order.hazardous_flag:
        return BotActionType.RENT_CONTAINER
    if order.priority == OrderPriority.URGENT and order.declared_waste_type == WasteType.RESIDUAL:
        return BotActionType.SCHEDULE_EARLY_EMPTY
    return BotActionType.ACCEPT_AND_ROUTE


def expected_outcome_for_order(order: DisposalOrder) -> ExpectedPath:
    if order.hazardous_flag and order.quantity_m3 >= 6:
        return ExpectedPath.REJECT
    if order.hazardous_flag:
        return ExpectedPath.ASK_FOR_APPROVAL
    if order.priority == OrderPriority.URGENT and order.declared_waste_type == WasteType.RESIDUAL:
        return ExpectedPath.ASK_FOR_APPROVAL
    return ExpectedPath.APPROVE
