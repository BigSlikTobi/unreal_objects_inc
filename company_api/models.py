"""API and state models for the waste-management company service."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class BotDecisionOutcome(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class CompanyStats(BaseModel):
    total_orders: int
    open_orders: int
    claimed_orders: int
    completed_orders: int
    rejected_orders: int
    blocked_orders: int
    active_containers: int
    rented_extra_containers: int
    overflow_count: int
    bankruptcy_count: int


class CompanyStatus(BaseModel):
    virtual_time: str | None
    current_run_started_at: str | None = None
    acceleration: int | None
    group_id: str | None
    deployment_mode: str = "local"
    public_voting_enabled: bool = False
    operator_auth_enabled: bool = False
    persistence_backend: str = "memory"
    bot_connected: bool
    bot_identity: str | None = None
    bot_last_seen_at: str | None = None
    current_run_id: int
    stats: CompanyStats


class ClockInfo(BaseModel):
    virtual_time: str
    acceleration: int
    is_business_hours: bool
    activity_multiplier: float
    day_of_week: str


class DisposalOrderDTO(BaseModel):
    order_id: str
    title: str
    customer_request: str
    declared_waste_type: str
    quantity_m3: float
    offered_price_eur: float
    priority: str
    service_window: str
    created_at: str
    customer_id: str | None = None
    site_id: str | None = None
    hazardous_flag: bool
    contamination_risk: bool
    status: str
    assigned_to: str | None = None
    bot_action: str | None = None
    action_payload: dict = Field(default_factory=dict)
    resolution: str | None = None
    decision_outcome: str | None = None
    decision_summary: str | None = None
    request_id: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    source_event_type: str | None = None
    source_event_source: str | None = None
    source_event_summary: str | None = None


class BotInboxOrderDTO(BaseModel):
    order_id: str
    title: str
    customer_request: str
    declared_waste_type: str
    quantity_m3: float
    offered_price_eur: float
    priority: str
    service_window: str
    created_at: str
    customer_id: str | None = None
    site_id: str | None = None
    status: str
    assigned_to: str | None = None


class OrdersResponse(BaseModel):
    orders: list[DisposalOrderDTO]
    total: int


class BotOrdersResponse(BaseModel):
    orders: list[BotInboxOrderDTO]
    total: int


class ContainerDTO(BaseModel):
    container_id: str
    label: str
    waste_type: str
    capacity_m3: float
    fill_level_m3: float
    fill_ratio: float
    rental_cost_per_cycle_eur: float
    early_empty_cost_eur: float
    emptying_interval_hours: int
    next_empty_at: str
    last_emptied_at: str
    is_rented_extra: bool
    overflowed: bool


class ContainersResponse(BaseModel):
    containers: list[ContainerDTO]
    total: int


class EconomicsSnapshot(BaseModel):
    revenue_eur: float
    invoiced_revenue_eur: float
    operating_cost_eur: float
    rental_cost_eur: float
    overhead_cost_eur: float
    penalty_cost_eur: float
    early_empty_cost_eur: float
    accounts_receivable_eur: float
    accounts_payable_eur: float
    cash_balance_eur: float
    daily_burn_eur: float
    profit_eur: float
    overflow_count: int
    bankruptcy_count: int
    current_run_id: int


class ReceivableEntry(BaseModel):
    entry_id: str
    order_id: str
    amount_eur: float
    issued_at: datetime
    due_at: datetime
    collected: bool = False


class PayableEntry(BaseModel):
    entry_id: str
    order_id: str | None = None
    amount_eur: float
    created_at: datetime
    due_at: datetime
    paid: bool = False
    category: str


class WasteEventDTO(BaseModel):
    event_id: str
    source: str
    event_type: str
    occurred_at: str
    summary: str
    customer_request: str | None = None
    internal_notes: str | None = None
    order_id: str | None = None


class EventsResponse(BaseModel):
    events: list[WasteEventDTO]
    total: int


class RuleDTO(BaseModel):
    id: str
    group_id: str | None = None
    group_name: str | None = None
    name: str
    feature: str
    active: bool
    datapoints: list[str]
    edge_cases: list[str]
    edge_cases_json: list[dict]
    rule_logic: str
    rule_logic_json: dict


class RuleGroupDTO(BaseModel):
    id: str
    name: str
    description: str = ""
    rule_count: int


class RulesResponse(BaseModel):
    rules: list[RuleDTO]
    group_id: str | None
    groups: list[RuleGroupDTO] = Field(default_factory=list)


class MarketPriceOptionDTO(BaseModel):
    option_id: str
    waste_type: str
    label: str
    category: str
    unit: str
    base_price_eur: float
    size_m3: float | None = None
    price_per_m3_eur: float | None = None
    price_per_kg_eur: float | None = None
    notes: str | None = None
    source_name: str
    source_url: str
    source_date: str | None = None


class OperationalPriceOptionDTO(BaseModel):
    option_id: str
    waste_type: str
    bot_action: str
    label: str
    capacity_m3: float | None = None
    rental_cost_per_cycle_eur: float | None = None
    early_empty_cost_eur: float | None = None
    turnaround_hours: int | None = None
    notes: str | None = None
    derived_from_source: str | None = None


class PricingCatalogResponse(BaseModel):
    currency: str
    market_quotes: list[MarketPriceOptionDTO]
    operational_options: list[OperationalPriceOptionDTO]


class ApprovalVoteSummary(BaseModel):
    approve_votes: int = 0
    reject_votes: int = 0
    total_votes: int = 0


class ApprovalDecisionMetadata(BaseModel):
    approved: bool
    reviewer: str
    rationale: str | None = None
    decided_at: str


class ApprovalItemDTO(BaseModel):
    request_id: str
    order_id: str
    title: str
    customer_request: str
    bot_action: str
    decision_summary: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    created_at: str
    status: str
    vote_summary: ApprovalVoteSummary = Field(default_factory=ApprovalVoteSummary)
    final_decision: ApprovalDecisionMetadata | None = None


class ApprovalsResponse(BaseModel):
    approvals: list[ApprovalItemDTO]
    total: int


class ApprovalVoteRequest(BaseModel):
    approved: bool


class ApprovalFinalizeRequest(BaseModel):
    approved: bool
    reviewer: str
    rationale: str | None = None


class ApprovalFinalizeResponse(BaseModel):
    request_id: str
    order_id: str
    status: str
    final_state: str


class OrderClaimRequest(BaseModel):
    bot_id: str


class OrderClaimResponse(BaseModel):
    order_id: str
    status: str
    assigned_to: str


class OrderResultSubmission(BaseModel):
    bot_id: str
    outcome: BotDecisionOutcome
    bot_action: str
    action_payload: dict = Field(default_factory=dict)
    decision_summary: str | None = None
    resolution: str | None = None
    request_id: str | None = None
    matched_rules: list[str] = Field(default_factory=list)


class OrderResultResponse(BaseModel):
    order_id: str
    status: str
    outcome: str
    request_id: str | None = None


class DisposalOrderWebhookPayload(BaseModel):
    orders: list[dict]


class ApprovalVoteState(BaseModel):
    approve_votes: int = 0
    reject_votes: int = 0


class OrderRecord(BaseModel):
    dto: DisposalOrderDTO
    sort_created_at: datetime
