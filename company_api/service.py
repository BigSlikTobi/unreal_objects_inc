"""In-memory runtime for the simulated waste-management company."""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from support_company.cost_policy import (
    DEFAULT_BANKRUPTCY_BURN_MULTIPLE as COST_POLICY_DEFAULT_BANKRUPTCY_BURN_MULTIPLE,
    DEFAULT_DAILY_OVERHEAD_EUR as COST_POLICY_DEFAULT_DAILY_OVERHEAD_EUR,
    BaselineOrderEconomics,
    CostPolicy,
    ProjectedEconomics,
    bankruptcy_threshold_eur,
    load_cost_policy,
    project_action_economics,
    project_order_economics,
)
from support_company.generator import generate_initial_containers
from support_company.models import CompanyEvent, DisposalOrder, GeneratedScenario, WasteContainer, WasteType
from support_company.pricing import (
    estimate_payment_delay_hours,
    estimate_service_cost,
    estimate_vendor_payment_delay_hours,
    list_market_price_options,
    list_operational_price_options,
)
from support_company.simulator import DEFAULT_LLM_MODEL, ScenarioGenerationConfig, generate_container_fleet, generate_scenarios

from .models import (
    ApprovalDecisionMetadata,
    ApprovalFinalizeResponse,
    ApprovalItemDTO,
    ApprovalVoteState,
    BaselineEconomicsDTO,
    BotDecisionOutcome,
    BotInboxOrderDTO,
    CompanyStats,
    CompanyStatus,
    ContainerDTO,
    DisposalOrderDTO,
    EconomicsSnapshot,
    EventsResponse,
    MarketPriceOptionDTO,
    OrderClaimResponse,
    OrderRecord,
    OrderResultResponse,
    OrderStatus,
    OperationalPriceOptionDTO,
    PayableEntry,
    ProjectedActionEconomicsDTO,
    ReceivableEntry,
    PricingCatalogResponse,
    RuleDTO,
    RuleGroupDTO,
    RulesResponse,
    WasteEventDTO,
)

CONTINUOUS_BOOTSTRAP_ORDERS = 2
DEFAULT_ACCELERATION = 24
DEFAULT_TARGET_ORDERS_PER_SIM_DAY = 1_000
DEFAULT_BANKRUPTCY_BURN_MULTIPLE = COST_POLICY_DEFAULT_BANKRUPTCY_BURN_MULTIPLE
DEFAULT_DAILY_OVERHEAD_EUR = COST_POLICY_DEFAULT_DAILY_OVERHEAD_EUR
OVERFLOW_PENALTY_EUR = 350.0


def utcnow() -> datetime:
    return datetime.now(UTC)


def isoformat(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat()


class CompanySimulationService:
    """Owns waste orders, containers, economics, and company restarts."""

    def __init__(
        self,
        rule_pack_path: str | Path,
        initial_order_count: int | None = 24,
        rolling_generation: bool = False,
        seed: int = 42,
        acceleration: int = DEFAULT_ACCELERATION,
        generator_mode: str = "mixed",
        rule_engine_url: str = "http://127.0.0.1:8001",
        decision_center_url: str = "http://127.0.0.1:8002",
        rule_group_id: str | None = None,
        llm_model: str = DEFAULT_LLM_MODEL,
        llm_api_key: str | None = None,
        allow_template_fallback: bool = True,
        deployment_mode: str = "local",
        public_voting_enabled: bool | None = None,
        operator_auth_enabled: bool | None = None,
        operator_token: str | None = None,
        internal_api_key: str | None = None,
        persistence_path: str | Path | None = None,
        bot_connection_timeout_seconds: int = 120,
        cost_policy_path: str | Path | None = None,
    ):
        self.rule_pack_path = Path(rule_pack_path)
        self.initial_order_count = initial_order_count
        self.rolling_generation = rolling_generation
        self.seed = seed
        self.acceleration = acceleration
        self.generator_mode = generator_mode
        self.rule_engine_url = rule_engine_url.rstrip("/")
        self.decision_center_url = decision_center_url.rstrip("/")
        self.internal_api_key = internal_api_key
        self.rule_group_id = rule_group_id
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.allow_template_fallback = allow_template_fallback
        self.deployment_mode = deployment_mode
        self.public_voting_enabled = public_voting_enabled if public_voting_enabled is not None else True
        self.operator_auth_enabled = operator_auth_enabled if operator_auth_enabled is not None else deployment_mode == "hosted"
        self.operator_token = operator_token
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.persistence_backend = "json" if self.persistence_path else "memory"
        self.bot_connection_timeout_seconds = bot_connection_timeout_seconds
        self.cost_policy: CostPolicy = load_cost_policy(cost_policy_path)
        self.continuous_mode = initial_order_count is None
        self.bounded_rolling_mode = rolling_generation and initial_order_count is not None and initial_order_count > 0

        self.group_id: str | None = None
        self.rules: list[RuleDTO] = []
        self.rule_groups: list[RuleGroupDTO] = []
        self.records: dict[str, OrderRecord] = {}
        self.source_orders: dict[str, DisposalOrder] = {}
        self.source_events: dict[str, CompanyEvent] = {}
        self.containers: dict[str, WasteContainer] = {}
        self.approval_votes: dict[str, ApprovalVoteState] = {}
        self.final_decisions: dict[str, ApprovalDecisionMetadata] = {}
        self._lock = asyncio.Lock()
        self._virtual_start = utcnow()
        self._real_start = utcnow()
        self._current_run_started_at = self._virtual_start
        self._last_financial_update = self._virtual_start
        self._order_seed_offset = 0
        self._current_run_id = 1
        self._arrival_rng = random.Random(seed + 91_337)
        self.bot_identity: str | None = None
        self.bot_last_seen_at: datetime | None = None

        self.invoiced_revenue_eur = 0.0
        self.revenue_eur = 0.0
        self.operating_cost_eur = 0.0
        self.rental_cost_eur = 0.0
        self.overhead_cost_eur = 0.0
        self.penalty_cost_eur = 0.0
        self.early_empty_cost_eur = 0.0
        self.cash_balance_eur = self.cost_policy.starting_cash_eur
        self.accounts_receivable_eur = 0.0
        self.accounts_payable_eur = 0.0
        self.receivables: list[ReceivableEntry] = []
        self.payables: list[PayableEntry] = []
        self.overflow_count = 0
        self.bankruptcy_count = 0

        self._continuous_task: asyncio.Task | None = None
        self._maintenance_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        pack = json.loads(self.rule_pack_path.read_text())
        self.rules = self._map_rules(pack["rules"])
        self.group_id = self.rule_group_id
        self.rule_groups = []
        if self.rule_group_id:
            await self._refresh_live_rules()
        else:
            await self._refresh_live_rule_catalog()
        restored = await self._load_persisted_state()
        if not restored:
            await self._reset_live_company_state(seed_offset=0)

        if self.bounded_rolling_mode:
            initial_count = min(CONTINUOUS_BOOTSTRAP_ORDERS, self.initial_order_count or 0)
        else:
            initial_count = self.initial_order_count if self.initial_order_count is not None else CONTINUOUS_BOOTSTRAP_ORDERS
        if not restored and initial_count > 0:
            await self._seed_orders(initial_count)

    def _map_rules(self, raw_rules: list[dict], group_id: str | None = None, group_name: str | None = None) -> list[RuleDTO]:
        return [
            RuleDTO(
                id=rule.get("id", f"rule-{idx + 1}"),
                group_id=group_id,
                group_name=group_name,
                name=rule["name"],
                feature=rule["feature"],
                active=rule["active"],
                datapoints=rule.get("datapoints", []),
                edge_cases=rule.get("edge_cases", []),
                edge_cases_json=rule.get("edge_cases_json", []),
                rule_logic=rule["rule_logic"],
                rule_logic_json=rule["rule_logic_json"],
            )
            for idx, rule in enumerate(raw_rules)
        ]

    async def start(self) -> None:
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        if self.continuous_mode or self.bounded_rolling_mode:
            self._continuous_task = asyncio.create_task(self._continuous_generation_loop())

    async def stop(self) -> None:
        for task in (self._continuous_task, self._maintenance_task):
            if task is None:
                continue
            task.cancel()
        for task in (self._continuous_task, self._maintenance_task):
            if task is None:
                continue
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def ingest_order(self, order: DisposalOrder) -> DisposalOrderDTO:
        dto = await self._store_order(order=order, event=None)
        await self._persist_state()
        return dto

    async def ingest_scenario(self, scenario: GeneratedScenario) -> DisposalOrderDTO:
        dto = await self._store_order(order=scenario.order, event=scenario.event)
        await self._persist_state()
        return dto

    async def _store_order(self, order: DisposalOrder, event: CompanyEvent | None) -> DisposalOrderDTO:
        created_at = order.created_at if order.created_at.tzinfo else order.created_at.replace(tzinfo=UTC)
        dto = DisposalOrderDTO(
            order_id=order.order_id,
            title=order.title,
            customer_request=order.customer_request,
            declared_waste_type=order.declared_waste_type.value,
            quantity_m3=order.quantity_m3,
            offered_price_eur=order.offered_price_eur,
            priority=order.priority.value,
            service_window=order.service_window.value,
            created_at=isoformat(created_at) or "",
            customer_id=order.customer_id,
            site_id=order.site_id,
            hazardous_flag=order.hazardous_flag,
            contamination_risk=order.contamination_risk,
            status=OrderStatus.OPEN.value,
            assigned_to=None,
            source_event_type=order.source_event_type.value if order.source_event_type else None,
            source_event_source=order.source_event_source.value if order.source_event_source else None,
            source_event_summary=order.source_event_summary,
        )
        async with self._lock:
            self.records[order.order_id] = OrderRecord(dto=dto, sort_created_at=created_at)
            self.source_orders[order.order_id] = order
            if event is not None:
                self.source_events[order.order_id] = event
        return dto

    def _current_financial_context(self) -> dict[str, object]:
        return {
            "current_cash_balance_eur": round(self.cash_balance_eur, 2),
            "current_accounts_receivable_eur": round(self.accounts_receivable_eur, 2),
            "current_accounts_payable_eur": round(self.accounts_payable_eur, 2),
            "current_net_working_capital_eur": round(self._net_working_capital_eur(), 2),
            "bankruptcy_threshold_eur": round(self._bankruptcy_threshold_eur(), 2),
            "cost_policy_version": self.cost_policy.version,
        }

    def _build_baseline_order_economics(self, order: DisposalOrder) -> BaselineOrderEconomics:
        return project_order_economics(
            policy=self.cost_policy,
            offered_price_eur=order.offered_price_eur,
            waste_type=order.declared_waste_type,
            quantity_m3=order.quantity_m3,
            service_window=order.service_window,
            contamination_risk=order.contamination_risk,
            hazardous_flag=order.hazardous_flag,
        )

    def _build_projected_action_economics(
        self,
        order: DisposalOrder,
        *,
        bot_action: str,
        action_payload: dict,
    ) -> ProjectedEconomics:
        return project_action_economics(
            policy=self.cost_policy,
            offered_price_eur=order.offered_price_eur,
            waste_type=order.declared_waste_type,
            quantity_m3=order.quantity_m3,
            service_window=order.service_window,
            contamination_risk=order.contamination_risk,
            hazardous_flag=order.hazardous_flag,
            bot_action=bot_action,
            action_payload=action_payload,
            current_cash_balance_eur=self.cash_balance_eur,
            accounts_receivable_eur=self.accounts_receivable_eur,
            accounts_payable_eur=self.accounts_payable_eur,
        )

    def _build_action_inputs(self, order: DisposalOrder) -> dict[str, object]:
        matching_containers = [
            container
            for container in self.containers.values()
            if container.waste_type == order.declared_waste_type
        ]
        route_options = sorted(
            [
                {
                    "target_container_id": container.container_id,
                    "label": container.label,
                    "target_waste_type": container.waste_type.value,
                    "available_capacity_m3": round(max(container.capacity_m3 - container.fill_level_m3, 0.0), 2),
                    "route_quantity_m3": order.quantity_m3,
                }
                for container in matching_containers
            ],
            key=lambda option: option["available_capacity_m3"],
            reverse=True,
        )
        early_empty_options = sorted(
            [
                {
                    "target_container_id": container.container_id,
                    "label": container.label,
                    "target_waste_type": container.waste_type.value,
                    "available_capacity_m3": round(max(container.capacity_m3 - container.fill_level_m3, 0.0), 2),
                    "recovered_capacity_m3": round(container.capacity_m3, 2),
                    "route_quantity_m3": order.quantity_m3,
                    "early_empty_cost_eur": round(container.early_empty_cost_eur, 2),
                    "emptying_interval_hours": container.emptying_interval_hours,
                }
                for container in matching_containers
            ],
            key=lambda option: option["early_empty_cost_eur"],
        )
        rental_options = []
        for option in list_operational_price_options(waste_type=order.declared_waste_type.value):
            if option["bot_action"] != "rent_container":
                continue
            rental_options.append(
                {
                    "option_id": option["option_id"],
                    "label": option["label"],
                    "target_waste_type": order.declared_waste_type.value,
                    "added_capacity_m3": option["capacity_m3"],
                    "extra_rental_cost_eur": option["rental_cost_per_cycle_eur"],
                    "early_empty_cost_eur": option["early_empty_cost_eur"],
                    "emptying_interval_hours": option["turnaround_hours"],
                    "route_quantity_m3": order.quantity_m3,
                }
            )
        return {
            "accept_and_route": {"options": route_options},
            "rent_container": {"options": rental_options},
            "schedule_early_empty": {"options": early_empty_options},
            "reject_order": {"reason_required": True},
        }

    def _hydrate_disposal_order_dto(self, record: OrderRecord) -> DisposalOrderDTO:
        dto = record.dto.model_copy(deep=True)
        order = self.source_orders.get(dto.order_id)
        if order is None:
            return dto
        baseline = self._build_baseline_order_economics(order)
        dto.baseline_economics = BaselineEconomicsDTO.model_validate(baseline.as_guardrail_context())
        dto.action_inputs = self._build_action_inputs(order)
        dto.guardrail_context_base = order.to_evaluation_context(
            baseline_economics=baseline.as_guardrail_context(),
            financial_context=self._current_financial_context(),
        )
        return dto

    def _to_bot_inbox_order(self, record: OrderRecord) -> BotInboxOrderDTO:
        dto = self._hydrate_disposal_order_dto(record)
        return BotInboxOrderDTO(
            order_id=dto.order_id,
            title=dto.title,
            customer_request=dto.customer_request,
            declared_waste_type=dto.declared_waste_type,
            quantity_m3=dto.quantity_m3,
            offered_price_eur=dto.offered_price_eur,
            priority=dto.priority,
            service_window=dto.service_window,
            created_at=dto.created_at,
            customer_id=dto.customer_id,
            site_id=dto.site_id,
            status=dto.status,
            assigned_to=dto.assigned_to,
            baseline_economics=dto.baseline_economics,
            projected_action_economics=dto.projected_action_economics,
            action_inputs=dto.action_inputs,
            guardrail_context_base=dto.guardrail_context_base,
        )

    async def claim_order(self, order_id: str, bot_id: str) -> OrderClaimResponse:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            record = self.records.get(order_id)
            if record is None:
                raise KeyError(order_id)
            if record.dto.status != OrderStatus.OPEN.value:
                raise ValueError(f"Order {order_id} is not open")
            record.dto.status = OrderStatus.CLAIMED.value
            record.dto.assigned_to = bot_id
            self._mark_bot_seen(bot_id)
            response = OrderClaimResponse(
                order_id=order_id,
                status=record.dto.status,
                assigned_to=bot_id,
                order=self._to_bot_inbox_order(record),
            )
        await self._persist_state()
        return response

    async def submit_order_result(
        self,
        order_id: str,
        bot_id: str,
        outcome: BotDecisionOutcome,
        bot_action: str,
        action_payload: dict | None = None,
        decision_summary: str | None = None,
        request_id: str | None = None,
        matched_rules: list[str] | None = None,
        resolution: str | None = None,
    ) -> OrderResultResponse:
        payload = action_payload or {}
        matched = matched_rules or []
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            record = self.records.get(order_id)
            if record is None:
                raise KeyError(order_id)
            if record.dto.status not in {OrderStatus.OPEN.value, OrderStatus.CLAIMED.value, OrderStatus.BLOCKED.value}:
                raise ValueError(f"Order {order_id} cannot accept a bot result from status {record.dto.status}")
            order = self.source_orders[order_id]

            record.dto.assigned_to = bot_id
            record.dto.request_id = request_id
            record.dto.matched_rules = matched
            record.dto.decision_outcome = outcome.value
            record.dto.decision_summary = decision_summary
            record.dto.bot_action = bot_action
            record.dto.action_payload = payload
            record.dto.projected_action_economics = ProjectedActionEconomicsDTO.model_validate(
                self._build_projected_action_economics(order, bot_action=bot_action, action_payload=payload).as_guardrail_context()
            )
            self._mark_bot_seen(bot_id)

            if outcome == BotDecisionOutcome.APPROVAL_REQUIRED:
                record.dto.status = OrderStatus.BLOCKED.value
                record.dto.resolution = resolution or "Bot is waiting for an external approval decision inside Unreal Objects."
                response = OrderResultResponse(order_id=order_id, status=record.dto.status, outcome=outcome.value, request_id=request_id)
                await self._persist_state_locked()
                return response

            if outcome == BotDecisionOutcome.REJECTED:
                record.dto.status = OrderStatus.REJECTED.value
                record.dto.resolution = resolution or "Guardrails blocked the chosen waste-handling action."
                response = OrderResultResponse(order_id=order_id, status=record.dto.status, outcome=outcome.value, request_id=request_id)
                await self._persist_state_locked()
                return response

            self._apply_approved_action(record.dto, order, bot_action=bot_action, payload=payload)
            await self._check_bankruptcy_locked()
            response = OrderResultResponse(order_id=order_id, status=record.dto.status, outcome=outcome.value, request_id=request_id)
            await self._persist_state_locked()
            return response

    async def get_status(self) -> CompanyStatus:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            orders = [record.dto for record in self.records.values()]
            containers = list(self.containers.values())

        stats = CompanyStats(
            total_orders=len(orders),
            open_orders=sum(order.status == OrderStatus.OPEN.value for order in orders),
            claimed_orders=sum(order.status == OrderStatus.CLAIMED.value for order in orders),
            completed_orders=sum(order.status == OrderStatus.COMPLETED.value for order in orders),
            rejected_orders=sum(order.status == OrderStatus.REJECTED.value for order in orders),
            blocked_orders=sum(order.status == OrderStatus.BLOCKED.value for order in orders),
            active_containers=len(containers),
            rented_extra_containers=sum(container.is_rented_extra for container in containers),
            overflow_count=self.overflow_count,
            bankruptcy_count=self.bankruptcy_count,
        )
        return CompanyStatus(
            virtual_time=isoformat(self._virtual_now()),
            current_run_started_at=isoformat(self._current_run_started_at),
            acceleration=self.acceleration,
            group_id=self.group_id,
            deployment_mode=self.deployment_mode,
            public_voting_enabled=self.public_voting_enabled,
            operator_auth_enabled=self.operator_auth_enabled,
            persistence_backend=self.persistence_backend,
            bot_connected=self._bot_is_connected(orders),
            bot_identity=self.bot_identity,
            bot_last_seen_at=isoformat(self.bot_last_seen_at),
            current_run_id=self._current_run_id,
            stats=stats,
        )

    async def get_clock(self):
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            current = self._virtual_now()
        hour = current.hour
        return {
            "virtual_time": isoformat(current) or "",
            "acceleration": self.acceleration,
            "is_business_hours": 6 <= hour < 20,
            "activity_multiplier": 1.6 if 6 <= hour < 20 else 0.7,
            "day_of_week": current.strftime("%A"),
        }

    async def get_orders(self) -> list[DisposalOrderDTO]:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            return [
                self._hydrate_disposal_order_dto(record)
                for record in sorted(self.records.values(), key=lambda record: record.sort_created_at, reverse=True)
            ]

    async def get_bot_orders(self) -> list[BotInboxOrderDTO]:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            return [
                self._to_bot_inbox_order(record)
                for record in sorted(self.records.values(), key=lambda record: record.sort_created_at, reverse=True)
            ]

    async def get_containers(self) -> list[ContainerDTO]:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            containers = list(self.containers.values())
        containers.sort(key=lambda container: (container.waste_type.value, container.label))
        return [self._container_to_dto(container) for container in containers]

    async def get_economics(self) -> EconomicsSnapshot:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            return EconomicsSnapshot(
                revenue_eur=round(self.revenue_eur, 2),
                invoiced_revenue_eur=round(self.invoiced_revenue_eur, 2),
                operating_cost_eur=round(self.operating_cost_eur, 2),
                rental_cost_eur=round(self.rental_cost_eur, 2),
                overhead_cost_eur=round(self.overhead_cost_eur, 2),
                penalty_cost_eur=round(self.penalty_cost_eur, 2),
                early_empty_cost_eur=round(self.early_empty_cost_eur, 2),
                accounts_receivable_eur=round(self.accounts_receivable_eur, 2),
                accounts_payable_eur=round(self.accounts_payable_eur, 2),
                cash_balance_eur=round(self.cash_balance_eur, 2),
                daily_burn_eur=round(self._daily_burn_eur(), 2),
                bankruptcy_threshold_eur=round(self._bankruptcy_threshold_eur(), 2),
                runway_days=round(self._runway_days(), 2),
                net_working_capital_eur=round(self._net_working_capital_eur(), 2),
                approval_locked_order_count=self._approval_locked_order_count(),
                approval_locked_revenue_eur=round(self._approval_locked_revenue_eur(), 2),
                profit_eur=round(self._profit(), 2),
                overflow_count=self.overflow_count,
                bankruptcy_count=self.bankruptcy_count,
                current_run_id=self._current_run_id,
            )

    async def get_rules(self) -> RulesResponse:
        await self._refresh_live_rule_catalog()
        return RulesResponse(rules=self.rules, group_id=self.group_id, groups=self.rule_groups)

    async def get_pricing(self, waste_type: str | None = None) -> PricingCatalogResponse:
        return PricingCatalogResponse(
            currency="EUR",
            market_quotes=[MarketPriceOptionDTO.model_validate(option) for option in list_market_price_options(waste_type=waste_type)],
            operational_options=[
                OperationalPriceOptionDTO.model_validate(option)
                for option in list_operational_price_options(waste_type=waste_type)
            ],
            policy=self.cost_policy.to_public_dict(),
        )

    async def get_events(self) -> EventsResponse:
        async with self._lock:
            events = [
                WasteEventDTO(
                    event_id=event.event_id,
                    source=event.source.value,
                    event_type=event.event_type.value,
                    occurred_at=isoformat(event.occurred_at) or "",
                    summary=event.summary,
                    customer_request=event.customer_request,
                    internal_notes=event.internal_notes,
                    order_id=order_id,
                )
                for order_id, event in self.source_events.items()
            ]
        events.sort(key=lambda event: event.occurred_at, reverse=True)
        return EventsResponse(events=events, total=len(events))

    async def get_approvals(self) -> list[ApprovalItemDTO]:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            items = [self._approval_item_from_record(record) for record in self.records.values() if record.dto.status == OrderStatus.BLOCKED.value]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items

    async def record_public_vote(self, request_id: str, approved: bool) -> ApprovalItemDTO:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            record = self._require_blocked_record_by_request_id(request_id)
            vote_state = self.approval_votes.setdefault(request_id, ApprovalVoteState())
            if approved:
                vote_state.approve_votes += 1
            else:
                vote_state.reject_votes += 1
            item = self._approval_item_from_record(record)
            await self._persist_state_locked()
            return item

    async def finalize_approval(self, request_id: str, approved: bool, reviewer: str, rationale: str | None = None) -> ApprovalFinalizeResponse:
        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            self._require_blocked_record_by_request_id(request_id)

        await self._submit_unreal_objects_approval(request_id=request_id, approved=approved, approver=reviewer)

        async with self._lock:
            self._refresh_runtime_locked(self._virtual_now())
            record = self._require_blocked_record_by_request_id(request_id)
            order = self.source_orders[record.dto.order_id]
            self.final_decisions[request_id] = ApprovalDecisionMetadata(
                approved=approved,
                reviewer=reviewer,
                rationale=rationale,
                decided_at=isoformat(self._virtual_now()) or "",
            )
            if approved:
                self._apply_approved_action(record.dto, order, bot_action=record.dto.bot_action or "", payload=record.dto.action_payload)
                record.dto.decision_outcome = BotDecisionOutcome.APPROVED.value
                if rationale:
                    record.dto.resolution = rationale
                await self._check_bankruptcy_locked()
                final_state = BotDecisionOutcome.APPROVED.value
            else:
                record.dto.status = OrderStatus.REJECTED.value
                record.dto.decision_outcome = BotDecisionOutcome.REJECTED.value
                record.dto.resolution = rationale or "Operator rejected the pending approval request."
                final_state = BotDecisionOutcome.REJECTED.value
            await self._persist_state_locked()
            return ApprovalFinalizeResponse(
                request_id=request_id,
                order_id=record.dto.order_id,
                status=record.dto.status,
                final_state=final_state,
            )

    async def _refresh_live_rule_catalog(self) -> None:
        try:
            groups = await self._fetch_live_rule_groups()
        except Exception:
            return
        self.rule_groups = [
            RuleGroupDTO(
                id=group["id"],
                name=group["name"],
                description=group.get("description", ""),
                rule_count=len(group.get("rules", [])),
            )
            for group in groups
        ]
        if self.rule_group_id:
            await self._refresh_live_rules(groups=groups)
            return

        live_rules: list[RuleDTO] = []
        for group in groups:
            live_rules.extend(
                self._map_rules(
                    group.get("rules", []),
                    group_id=group.get("id"),
                    group_name=group.get("name"),
                )
            )
        if live_rules:
            self.rules = live_rules
            self.group_id = None

    async def _refresh_live_rules(self, groups: list[dict] | None = None) -> None:
        if not self.rule_group_id:
            return
        payload: dict | None = None
        if groups is not None:
            payload = next((group for group in groups if group.get("id") == self.rule_group_id), None)
        if payload is None:
            try:
                payload = await self._fetch_live_rule_group(self.rule_group_id)
            except Exception:
                return
        self.group_id = payload.get("id", self.rule_group_id)
        self.rules = self._map_rules(
            payload.get("rules", []),
            group_id=payload.get("id", self.rule_group_id),
            group_name=payload.get("name"),
        )

    async def _fetch_live_rule_group(self, group_id: str) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.rule_engine_url}/v1/groups/{group_id}")
            response.raise_for_status()
            return response.json()

    async def _fetch_live_rule_groups(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.rule_engine_url}/v1/groups")
            response.raise_for_status()
            return response.json()

    async def _seed_orders(self, count: int) -> None:
        scenarios = generate_scenarios(
            ScenarioGenerationConfig(
                count=count,
                seed=self.seed + self._order_seed_offset,
                mode=self.generator_mode,
                allow_template_fallback=self.allow_template_fallback,
                model=self.llm_model,
                api_key=self.llm_api_key,
                cost_policy=self.cost_policy,
            )
        )
        self._order_seed_offset += count
        for scenario in scenarios:
            await self.ingest_scenario(scenario)

    async def _continuous_generation_loop(self) -> None:
        while True:
            if self.bounded_rolling_mode and self.initial_order_count is not None and self._order_seed_offset >= self.initial_order_count:
                break
            await asyncio.sleep(self._next_generation_delay_seconds())
            if self.bounded_rolling_mode and self.initial_order_count is not None:
                remaining = self.initial_order_count - self._order_seed_offset
                if remaining <= 0:
                    break
                await self._seed_orders(min(1, remaining))
                continue
            await self._seed_orders(1)

    async def _maintenance_loop(self) -> None:
        while True:
            await asyncio.sleep(max(1.0, 60 / max(self.acceleration, 1)))
            async with self._lock:
                self._refresh_runtime_locked(self._virtual_now())
                await self._persist_state_locked()

    async def _reset_live_company_state(self, seed_offset: int) -> None:
        async with self._lock:
            now = self._virtual_now()
            self._current_run_started_at = now
            self._last_financial_update = now
            self.records = {}
            self.source_orders = {}
            self.source_events = {}
            self.containers = {
                container.container_id: container
                for container in generate_container_fleet(seed=self.seed + seed_offset, now=now)
            }
            self.approval_votes = {}
            self.final_decisions = {}
            self.bot_identity = None
            self.bot_last_seen_at = None
            self.receivables = []
            self.payables = []
            self.invoiced_revenue_eur = 0.0
            self.revenue_eur = 0.0
            self.operating_cost_eur = 0.0
            self.rental_cost_eur = 0.0
            self.overhead_cost_eur = 0.0
            self.penalty_cost_eur = 0.0
            self.early_empty_cost_eur = 0.0
            self.cash_balance_eur = self.cost_policy.starting_cash_eur
            self.accounts_receivable_eur = 0.0
            self.accounts_payable_eur = 0.0

    def _apply_approved_action(
        self,
        dto: DisposalOrderDTO,
        order: DisposalOrder,
        bot_action: str,
        payload: dict,
    ) -> None:
        now = self._virtual_now()
        if bot_action == "reject_order":
            dto.status = OrderStatus.REJECTED.value
            dto.resolution = payload.get("reason") or "Bot chose to reject the disposal order."
            return

        if bot_action == "accept_and_route":
            container = self._require_container(payload.get("target_container_id"))
            quantity = float(payload.get("route_quantity_m3", order.quantity_m3))
            self._route_into_container(container, order, quantity)
            self._record_completed_order_finance(order, completed_at=now)
            dto.status = OrderStatus.COMPLETED.value
            dto.resolution = f"Order routed into {container.label}."
            return

        if bot_action == "rent_container":
            waste_type = WasteType(payload.get("target_waste_type", order.declared_waste_type.value))
            capacity = float(payload.get("added_capacity_m3", max(order.quantity_m3 * 1.5, 8.0)))
            rental = float(payload.get("extra_rental_cost_eur", 420.0))
            new_container = WasteContainer(
                label=f"Rented {waste_type.value.title()} Unit",
                waste_type=waste_type,
                capacity_m3=capacity,
                fill_level_m3=0.0,
                rental_cost_per_cycle_eur=rental,
                early_empty_cost_eur=float(payload.get("early_empty_cost_eur", 180.0)),
                emptying_interval_hours=int(payload.get("emptying_interval_hours", 24)),
                last_emptied_at=now,
                next_empty_at=now + timedelta(hours=int(payload.get("emptying_interval_hours", 24))),
                is_rented_extra=True,
            )
            self.containers[new_container.container_id] = new_container
            setup_cost = min(120.0, round(rental * 0.25, 2))
            self._record_payable(
                amount_eur=setup_cost,
                created_at=now,
                due_at=now + timedelta(hours=12),
                category="extra_rental_setup",
                order_id=order.order_id,
            )
            quantity = float(payload.get("route_quantity_m3", order.quantity_m3))
            self._route_into_container(new_container, order, quantity)
            self._record_completed_order_finance(order, completed_at=now)
            dto.status = OrderStatus.COMPLETED.value
            dto.resolution = f"Rented extra {waste_type.value} capacity and routed the order."
            return

        if bot_action == "schedule_early_empty":
            container = self._require_container(payload.get("target_container_id"))
            container.fill_level_m3 = 0.0
            container.overflowed = False
            container.last_emptied_at = now
            container.next_empty_at = now + timedelta(hours=container.emptying_interval_hours)
            self.early_empty_cost_eur += container.early_empty_cost_eur
            self._record_payable(
                amount_eur=container.early_empty_cost_eur,
                created_at=now,
                due_at=now + timedelta(hours=12),
                category="early_empty",
                order_id=order.order_id,
            )
            quantity = float(payload.get("route_quantity_m3", order.quantity_m3))
            self._route_into_container(container, order, quantity)
            self._record_completed_order_finance(order, completed_at=now)
            dto.status = OrderStatus.COMPLETED.value
            dto.resolution = f"Triggered early emptying for {container.label} and routed the order."
            return

        raise ValueError(f"Unsupported bot action: {bot_action}")

    def _route_into_container(self, container: WasteContainer, order: DisposalOrder, quantity: float) -> None:
        if container.waste_type != order.declared_waste_type:
            raise ValueError("Target container waste type does not match the order waste type")
        container.fill_level_m3 += quantity
        if container.fill_level_m3 > container.capacity_m3:
            container.overflowed = True
            self.overflow_count += 1
            self.penalty_cost_eur += self.cost_policy.overflow_penalty_eur
            self.cash_balance_eur -= self.cost_policy.overflow_penalty_eur
            container.fill_level_m3 = container.capacity_m3

    def _require_container(self, container_id: str | None) -> WasteContainer:
        if not container_id or container_id not in self.containers:
            raise ValueError("A valid target_container_id is required")
        return self.containers[container_id]

    async def _check_bankruptcy_locked(self) -> None:
        if self.cash_balance_eur > self._bankruptcy_threshold_eur():
            return
        self.bankruptcy_count += 1
        self._current_run_id += 1
        now = self._virtual_now()
        self._reset_after_bankruptcy_locked(now)

    def _reset_after_bankruptcy_locked(self, now: datetime) -> None:
        self._current_run_started_at = now
        self._last_financial_update = now
        self.records = {}
        self.source_orders = {}
        self.source_events = {}
        self.approval_votes = {}
        self.final_decisions = {}
        self.bot_identity = None
        self.bot_last_seen_at = None
        self.receivables = []
        self.payables = []
        self.containers = {
            container.container_id: container
            for container in generate_initial_containers(seed=self.seed + self._current_run_id, now=now)
        }
        self.invoiced_revenue_eur = 0.0
        self.revenue_eur = 0.0
        self.operating_cost_eur = 0.0
        self.rental_cost_eur = 0.0
        self.overhead_cost_eur = 0.0
        self.penalty_cost_eur = 0.0
        self.early_empty_cost_eur = 0.0
        self.cash_balance_eur = self.cost_policy.starting_cash_eur
        self.accounts_receivable_eur = 0.0
        self.accounts_payable_eur = 0.0

    def _container_to_dto(self, container: WasteContainer) -> ContainerDTO:
        fill_ratio = 0.0 if container.capacity_m3 <= 0 else container.fill_level_m3 / container.capacity_m3
        return ContainerDTO(
            container_id=container.container_id,
            label=container.label,
            waste_type=container.waste_type.value,
            capacity_m3=container.capacity_m3,
            fill_level_m3=round(container.fill_level_m3, 2),
            fill_ratio=round(fill_ratio, 3),
            rental_cost_per_cycle_eur=container.rental_cost_per_cycle_eur,
            early_empty_cost_eur=container.early_empty_cost_eur,
            emptying_interval_hours=container.emptying_interval_hours,
            next_empty_at=isoformat(container.next_empty_at) or "",
            last_emptied_at=isoformat(container.last_emptied_at) or "",
            is_rented_extra=container.is_rented_extra,
            overflowed=container.overflowed,
        )

    def _profit(self) -> float:
        return self.revenue_eur - self.operating_cost_eur - self.rental_cost_eur - self.overhead_cost_eur - self.penalty_cost_eur - self.early_empty_cost_eur

    def _bankruptcy_threshold_eur(self) -> float:
        return bankruptcy_threshold_eur(policy=self.cost_policy)

    def _baseline_cycle_cost_eur(self) -> float:
        return 0.0

    def _daily_burn_eur(self) -> float:
        return self.cost_policy.daily_overhead_eur

    def _net_working_capital_eur(self) -> float:
        return self.cash_balance_eur + self.accounts_receivable_eur - self.accounts_payable_eur

    def _runway_days(self) -> float:
        daily_burn = self._daily_burn_eur()
        if daily_burn <= 0:
            return 0.0
        return (self.cash_balance_eur - self._bankruptcy_threshold_eur()) / daily_burn

    def _approval_locked_order_count(self) -> int:
        return sum(record.dto.status == OrderStatus.BLOCKED.value for record in self.records.values())

    def _approval_locked_revenue_eur(self) -> float:
        return sum(record.dto.offered_price_eur for record in self.records.values() if record.dto.status == OrderStatus.BLOCKED.value)

    def _next_generation_delay_seconds(self) -> float:
        real_seconds_per_sim_day = timedelta(days=1).total_seconds() / max(self.acceleration, 1)
        average_delay = real_seconds_per_sim_day / DEFAULT_TARGET_ORDERS_PER_SIM_DAY
        return self._arrival_rng.uniform(average_delay * 0.75, average_delay * 1.25)

    def _virtual_now(self) -> datetime:
        elapsed = utcnow() - self._real_start
        return self._virtual_start + timedelta(seconds=elapsed.total_seconds() * self.acceleration)

    def _refresh_runtime_locked(self, now: datetime) -> None:
        self._advance_financials_locked(now)
        if self.cash_balance_eur <= self._bankruptcy_threshold_eur():
            self.bankruptcy_count += 1
            self._current_run_id += 1
            self._reset_after_bankruptcy_locked(now)
            return
        for container in self.containers.values():
            while container.next_empty_at <= now:
                empty_at = container.next_empty_at
                if container.fill_level_m3 > 0.05:
                    self._record_scheduled_exchange(container, emptied_at=empty_at)
                container.fill_level_m3 = 0.0
                container.overflowed = False
                container.last_emptied_at = empty_at
                container.next_empty_at = empty_at + timedelta(hours=container.emptying_interval_hours)

    def _advance_financials_locked(self, now: datetime) -> None:
        if now <= self._last_financial_update:
            return
        elapsed_hours = (now - self._last_financial_update).total_seconds() / 3600
        hourly_overhead = self.cost_policy.daily_overhead_eur / 24
        self.overhead_cost_eur += hourly_overhead * elapsed_hours
        self.cash_balance_eur -= hourly_overhead * elapsed_hours

        for receivable in self.receivables:
            if not receivable.collected and receivable.due_at <= now:
                receivable.collected = True
                self.accounts_receivable_eur -= receivable.amount_eur
                self.revenue_eur += receivable.amount_eur
                self.cash_balance_eur += receivable.amount_eur

        for payable in self.payables:
            if not payable.paid and payable.due_at <= now:
                payable.paid = True
                self.accounts_payable_eur -= payable.amount_eur
                self.cash_balance_eur -= payable.amount_eur

        self.accounts_receivable_eur = max(0.0, self.accounts_receivable_eur)
        self.accounts_payable_eur = max(0.0, self.accounts_payable_eur)
        self._last_financial_update = now

    def _record_completed_order_finance(self, order: DisposalOrder, completed_at: datetime) -> None:
        invoice_due_at = completed_at + timedelta(hours=estimate_payment_delay_hours(order.service_window, policy=self.cost_policy))
        invoice = ReceivableEntry(
            entry_id=str(uuid.uuid4()),
            order_id=order.order_id,
            amount_eur=order.offered_price_eur,
            issued_at=completed_at,
            due_at=invoice_due_at,
        )
        self.receivables.append(invoice)
        self.invoiced_revenue_eur += order.offered_price_eur
        self.accounts_receivable_eur += order.offered_price_eur

        service_cost = estimate_service_cost(
            waste_type=order.declared_waste_type,
            quantity_m3=order.quantity_m3,
            service_window=order.service_window,
            contamination_risk=order.contamination_risk,
            hazardous_flag=order.hazardous_flag,
            policy=self.cost_policy,
        )
        self.operating_cost_eur += service_cost
        payable_due_at = completed_at + timedelta(
            hours=estimate_vendor_payment_delay_hours(
                order.service_window,
                order.hazardous_flag,
                policy=self.cost_policy,
            )
        )
        self._record_payable(
            amount_eur=service_cost,
            created_at=completed_at,
            due_at=payable_due_at,
            category="service_cost",
            order_id=order.order_id,
        )

    def _record_payable(
        self,
        *,
        amount_eur: float,
        created_at: datetime,
        due_at: datetime,
        category: str,
        order_id: str | None = None,
    ) -> None:
        payable = PayableEntry(
            entry_id=str(uuid.uuid4()),
            order_id=order_id,
            amount_eur=amount_eur,
            created_at=created_at,
            due_at=due_at,
            category=category,
        )
        self.payables.append(payable)
        self.accounts_payable_eur += amount_eur

    def _record_scheduled_exchange(self, container: WasteContainer, *, emptied_at: datetime) -> None:
        exchange_cost = round(container.rental_cost_per_cycle_eur, 2)
        if exchange_cost <= 0:
            return
        self.rental_cost_eur += exchange_cost
        self._record_payable(
            amount_eur=exchange_cost,
            created_at=emptied_at,
            due_at=emptied_at + timedelta(hours=12),
            category="pickup_exchange",
        )

    def _mark_bot_seen(self, bot_id: str) -> None:
        self.bot_identity = bot_id
        self.bot_last_seen_at = utcnow()

    def _bot_is_connected(self, orders: list[DisposalOrderDTO]) -> bool:
        if any(order.status in {OrderStatus.CLAIMED.value, OrderStatus.BLOCKED.value} for order in orders):
            return True
        if self.bot_last_seen_at is None:
            return False
        return utcnow() - self.bot_last_seen_at <= timedelta(seconds=self.bot_connection_timeout_seconds)

    def _require_blocked_record_by_request_id(self, request_id: str) -> OrderRecord:
        for record in self.records.values():
            if record.dto.request_id == request_id and record.dto.status == OrderStatus.BLOCKED.value:
                return record
        raise KeyError(request_id)

    def _approval_item_from_record(self, record: OrderRecord) -> ApprovalItemDTO:
        dto = self._hydrate_disposal_order_dto(record)
        request_id = record.dto.request_id or ""
        votes = self.approval_votes.get(request_id, ApprovalVoteState())
        return ApprovalItemDTO(
            request_id=request_id,
            order_id=dto.order_id,
            title=dto.title,
            customer_request=dto.customer_request,
            bot_action=dto.bot_action or "unknown",
            baseline_economics=dto.baseline_economics,
            projected_action_economics=dto.projected_action_economics,
            decision_summary=dto.decision_summary,
            matched_rules=list(dto.matched_rules),
            created_at=dto.created_at,
            status=dto.status,
            vote_summary={
                "approve_votes": votes.approve_votes,
                "reject_votes": votes.reject_votes,
                "total_votes": votes.approve_votes + votes.reject_votes,
            },
            final_decision=self.final_decisions.get(request_id),
        )

    async def _submit_unreal_objects_approval(self, request_id: str, approved: bool, approver: str) -> None:
        headers = {}
        if self.internal_api_key:
            headers["X-Internal-Key"] = self.internal_api_key
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.decision_center_url}/v1/decide/{request_id}/approve",
                json={"approved": approved, "approver": approver},
                headers=headers,
            )
            response.raise_for_status()

    async def _persist_state(self) -> None:
        async with self._lock:
            await self._persist_state_locked()

    async def _persist_state_locked(self) -> None:
        if self.persistence_path is None:
            return
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "virtual_start": isoformat(self._virtual_start),
            "real_start": isoformat(self._real_start),
            "current_run_started_at": isoformat(self._current_run_started_at),
            "last_financial_update": isoformat(self._last_financial_update),
            "order_seed_offset": self._order_seed_offset,
            "current_run_id": self._current_run_id,
            "bot_identity": self.bot_identity,
            "bot_last_seen_at": isoformat(self.bot_last_seen_at),
            "invoiced_revenue_eur": self.invoiced_revenue_eur,
            "revenue_eur": self.revenue_eur,
            "operating_cost_eur": self.operating_cost_eur,
            "rental_cost_eur": self.rental_cost_eur,
            "overhead_cost_eur": self.overhead_cost_eur,
            "penalty_cost_eur": self.penalty_cost_eur,
            "early_empty_cost_eur": self.early_empty_cost_eur,
            "cash_balance_eur": self.cash_balance_eur,
            "cost_policy": self.cost_policy.to_public_dict(),
            "accounts_receivable_eur": self.accounts_receivable_eur,
            "accounts_payable_eur": self.accounts_payable_eur,
            "overflow_count": self.overflow_count,
            "bankruptcy_count": self.bankruptcy_count,
            "receivables": [entry.model_dump(mode="json") for entry in self.receivables],
            "payables": [entry.model_dump(mode="json") for entry in self.payables],
            "records": [record.model_dump(mode="json") for record in self.records.values()],
            "source_orders": {order_id: order.model_dump(mode="json") for order_id, order in self.source_orders.items()},
            "source_events": {order_id: event.model_dump(mode="json") for order_id, event in self.source_events.items()},
            "containers": {container_id: container.model_dump(mode="json") for container_id, container in self.containers.items()},
            "approval_votes": {request_id: state.model_dump(mode="json") for request_id, state in self.approval_votes.items()},
            "final_decisions": {request_id: state.model_dump(mode="json") for request_id, state in self.final_decisions.items()},
        }
        self.persistence_path.write_text(json.dumps(snapshot, indent=2))

    async def _load_persisted_state(self) -> bool:
        if self.persistence_path is None or not self.persistence_path.exists():
            return False
        payload = json.loads(self.persistence_path.read_text())
        async with self._lock:
            self._virtual_start = datetime.fromisoformat(payload["virtual_start"])
            self._real_start = utcnow()
            self._current_run_started_at = (
                datetime.fromisoformat(payload["current_run_started_at"])
                if payload.get("current_run_started_at")
                else self._virtual_start
            )
            self._last_financial_update = (
                datetime.fromisoformat(payload["last_financial_update"])
                if payload.get("last_financial_update")
                else self._virtual_start
            )
            self._order_seed_offset = payload.get("order_seed_offset", 0)
            self._current_run_id = payload.get("current_run_id", 1)
            self.bot_identity = payload.get("bot_identity")
            self.bot_last_seen_at = (
                datetime.fromisoformat(payload["bot_last_seen_at"])
                if payload.get("bot_last_seen_at")
                else None
            )
            self.invoiced_revenue_eur = payload.get("invoiced_revenue_eur", 0.0)
            self.revenue_eur = payload.get("revenue_eur", 0.0)
            self.operating_cost_eur = payload.get("operating_cost_eur", 0.0)
            self.rental_cost_eur = payload.get("rental_cost_eur", 0.0)
            self.overhead_cost_eur = payload.get("overhead_cost_eur", 0.0)
            self.penalty_cost_eur = payload.get("penalty_cost_eur", 0.0)
            self.early_empty_cost_eur = payload.get("early_empty_cost_eur", 0.0)
            self.cash_balance_eur = payload.get("cash_balance_eur", self.cost_policy.starting_cash_eur)
            self.accounts_receivable_eur = payload.get("accounts_receivable_eur", 0.0)
            self.accounts_payable_eur = payload.get("accounts_payable_eur", 0.0)
            self.overflow_count = payload.get("overflow_count", 0)
            self.bankruptcy_count = payload.get("bankruptcy_count", 0)
            self.receivables = [
                ReceivableEntry.model_validate(entry_payload)
                for entry_payload in payload.get("receivables", [])
            ]
            self.payables = [
                PayableEntry.model_validate(entry_payload)
                for entry_payload in payload.get("payables", [])
            ]
            self.records = {
                record_payload["dto"]["order_id"]: OrderRecord.model_validate(record_payload)
                for record_payload in payload.get("records", [])
            }
            self.source_orders = {
                order_id: DisposalOrder.model_validate(order_payload)
                for order_id, order_payload in payload.get("source_orders", {}).items()
            }
            self.source_events = {
                order_id: CompanyEvent.model_validate(event_payload)
                for order_id, event_payload in payload.get("source_events", {}).items()
            }
            self.containers = {
                container_id: WasteContainer.model_validate(container_payload)
                for container_id, container_payload in payload.get("containers", {}).items()
            }
            self.approval_votes = {
                request_id: ApprovalVoteState.model_validate(state_payload)
                for request_id, state_payload in payload.get("approval_votes", {}).items()
            }
            self.final_decisions = {
                request_id: ApprovalDecisionMetadata.model_validate(state_payload)
                for request_id, state_payload in payload.get("final_decisions", {}).items()
            }
        return True
