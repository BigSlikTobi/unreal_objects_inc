"""Domain models for the waste-management company simulation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field


class WasteType(str, Enum):
    RESIDUAL = "residual"
    RECYCLING = "recycling"
    PAPER = "paper"
    GLASS = "glass"
    ORGANIC = "organic"
    HAZARDOUS = "hazardous"


class OrderPriority(str, Enum):
    STANDARD = "standard"
    URGENT = "urgent"


class ServiceWindow(str, Enum):
    SAME_DAY = "same_day"
    NEXT_DAY = "next_day"
    SCHEDULED = "scheduled"


class EventSource(str, Enum):
    CUSTOMER = "customer"
    OPERATIONS = "operations"
    MARKET = "market"


class EventType(str, Enum):
    DISPOSAL_ORDER_REQUEST = "disposal_order_request"
    EMPTYING_DUE = "emptying_due"
    OVERFLOW_ALERT = "overflow_alert"
    COST_PRESSURE = "cost_pressure"


class ExpectedPath(str, Enum):
    APPROVE = "APPROVE"
    ASK_FOR_APPROVAL = "ASK_FOR_APPROVAL"
    REJECT = "REJECT"


class BotActionType(str, Enum):
    ACCEPT_AND_ROUTE = "accept_and_route"
    REJECT_ORDER = "reject_order"
    RENT_CONTAINER = "rent_container"
    SCHEDULE_EARLY_EMPTY = "schedule_early_empty"


class DisposalOrder(BaseModel):
    """A customer disposal order the bot must handle."""

    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    customer_request: str
    declared_waste_type: WasteType
    quantity_m3: float = Field(gt=0)
    offered_price_eur: float = Field(ge=0)
    priority: OrderPriority = OrderPriority.STANDARD
    service_window: ServiceWindow = ServiceWindow.NEXT_DAY
    customer_id: str | None = None
    site_id: str | None = None
    hazardous_flag: bool = False
    contamination_risk: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    source_event_id: str | None = None
    source_event_type: EventType | None = None
    source_event_source: EventSource | None = None
    source_event_summary: str | None = None

    def to_evaluation_context(
        self,
        bot_action: str | None = None,
        action_payload: dict | None = None,
        baseline_economics: dict | None = None,
        projected_action_economics: dict | None = None,
        financial_context: dict | None = None,
    ) -> dict:
        """Convert an order and optional chosen action into a guardrail context."""
        ctx = {
            "declared_waste_type": self.declared_waste_type.value,
            "quantity_m3": self.quantity_m3,
            "offered_price_eur": self.offered_price_eur,
            "priority": self.priority.value,
            "service_window": self.service_window.value,
            "hazardous_flag": self.hazardous_flag,
            "contamination_risk": self.contamination_risk,
        }
        if baseline_economics:
            ctx.update(baseline_economics)
        if financial_context:
            ctx.update(financial_context)
        if bot_action:
            ctx["bot_action"] = bot_action
        if action_payload:
            if "target_waste_type" in action_payload:
                ctx["target_waste_type"] = action_payload["target_waste_type"]
            if "target_container_type" in action_payload:
                ctx["target_container_type"] = action_payload["target_container_type"]
            if "available_capacity_m3" in action_payload:
                ctx["available_capacity_m3"] = action_payload["available_capacity_m3"]
            if "route_quantity_m3" in action_payload:
                ctx["route_quantity_m3"] = action_payload["route_quantity_m3"]
            if "added_capacity_m3" in action_payload:
                ctx["added_capacity_m3"] = action_payload["added_capacity_m3"]
            if "extra_rental_cost_eur" in action_payload:
                ctx["extra_rental_cost_eur"] = action_payload["extra_rental_cost_eur"]
            if "early_empty_cost_eur" in action_payload:
                ctx["early_empty_cost_eur"] = action_payload["early_empty_cost_eur"]
        if projected_action_economics:
            ctx.update(projected_action_economics)
        return ctx


class WasteContainer(BaseModel):
    """A physical or rented waste container managed by the company."""

    container_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    waste_type: WasteType
    capacity_m3: float = Field(gt=0)
    fill_level_m3: float = Field(ge=0)
    rental_cost_per_cycle_eur: float = Field(ge=0)
    early_empty_cost_eur: float = Field(ge=0)
    emptying_interval_hours: int = Field(gt=0)
    next_empty_at: datetime
    last_emptied_at: datetime
    is_rented_extra: bool = False
    overflowed: bool = False


class CompanyOperationSnapshot(BaseModel):
    """Operational context used when generating realistic disposal orders."""

    operating_window: str
    demand_level: str
    depot_load: str
    business_note: str


class CompanyEvent(BaseModel):
    """A raw company event from which an order can be derived."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: EventSource
    event_type: EventType
    occurred_at: datetime = Field(default_factory=datetime.now)
    site_id: str | None = None
    customer_id: str | None = None
    summary: str
    customer_request: str | None = None
    internal_notes: str | None = None


class GeneratedScenario(BaseModel):
    """A realistic order scenario used for simulation and testing."""

    operations: CompanyOperationSnapshot
    event: CompanyEvent
    order: DisposalOrder
    expected_action: BotActionType
    expected_outcome: ExpectedPath


class GeneratedScenarioBatch(BaseModel):
    """Batch of generated scenarios used by the simulator."""

    scenarios: list[GeneratedScenario]
