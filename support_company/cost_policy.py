"""Shared cost policy and economics projections for the waste company."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json

from .models import ServiceWindow, WasteType


DEFAULT_STARTING_CASH_EUR = 70_000.0
DEFAULT_DAILY_OVERHEAD_EUR = 750.0
DEFAULT_BANKRUPTCY_BURN_MULTIPLE = 20.0
DEFAULT_MIN_MARGIN_PCT_FOR_APPROVAL = 0.18
DEFAULT_MIN_MARGIN_PCT_FOR_AUTO_APPROVE = 0.32
DEFAULT_MAX_CASH_GAP_HOURS = 48

WASTE_DENSITY_KG_PER_M3 = {
    WasteType.RESIDUAL.value: 140.0,
    WasteType.RECYCLING.value: 95.0,
    WasteType.PAPER.value: 60.0,
    WasteType.GLASS.value: 380.0,
    WasteType.ORGANIC.value: 320.0,
    WasteType.HAZARDOUS.value: 40.0,
}

DEFAULT_QUOTE_MARGIN_MULTIPLIER = {
    WasteType.RESIDUAL.value: 1.14,
    WasteType.RECYCLING.value: 1.12,
    WasteType.PAPER.value: 1.20,
    WasteType.GLASS.value: 1.12,
    WasteType.ORGANIC.value: 1.18,
    WasteType.HAZARDOUS.value: 1.16,
}

DEFAULT_SERVICE_BASE_COST_EUR = {
    WasteType.RESIDUAL.value: 44.0,
    WasteType.RECYCLING.value: 28.0,
    WasteType.PAPER.value: 16.0,
    WasteType.GLASS.value: 34.0,
    WasteType.ORGANIC.value: 30.0,
    WasteType.HAZARDOUS.value: 92.0,
}

DEFAULT_SERVICE_COST_PER_M3_EUR = {
    WasteType.RESIDUAL.value: 8.0,
    WasteType.RECYCLING.value: 5.5,
    WasteType.PAPER.value: 3.25,
    WasteType.GLASS.value: 8.5,
    WasteType.ORGANIC.value: 8.5,
    WasteType.HAZARDOUS.value: 26.0,
}

DEFAULT_SERVICE_WINDOW_PRICE_MULTIPLIER = {
    ServiceWindow.SAME_DAY.value: 1.18,
    ServiceWindow.NEXT_DAY.value: 1.05,
    ServiceWindow.SCHEDULED.value: 1.0,
}

DEFAULT_SERVICE_WINDOW_COST_MULTIPLIER = {
    ServiceWindow.SAME_DAY.value: 1.14,
    ServiceWindow.NEXT_DAY.value: 1.03,
    ServiceWindow.SCHEDULED.value: 0.92,
}

DEFAULT_PAYMENT_DELAY_HOURS = {
    ServiceWindow.SAME_DAY.value: 6,
    ServiceWindow.NEXT_DAY.value: 18,
    ServiceWindow.SCHEDULED.value: 30,
}

DEFAULT_VENDOR_PAYMENT_DELAY_HOURS = {
    ServiceWindow.SAME_DAY.value: 12,
    ServiceWindow.NEXT_DAY.value: 24,
    ServiceWindow.SCHEDULED.value: 36,
}


@dataclass(frozen=True)
class BaselineOrderEconomics:
    customer_price_eur: float
    baseline_service_cost_eur: float
    baseline_total_cost_eur: float
    baseline_margin_eur: float
    baseline_margin_pct: float
    baseline_receivable_delay_hours: int
    baseline_payable_delay_hours: int
    baseline_cash_gap_hours: int

    def as_guardrail_context(self) -> dict[str, float | int]:
        return {
            "customer_price_eur": self.customer_price_eur,
            "baseline_service_cost_eur": self.baseline_service_cost_eur,
            "baseline_total_cost_eur": self.baseline_total_cost_eur,
            "baseline_margin_eur": self.baseline_margin_eur,
            "baseline_margin_pct": self.baseline_margin_pct,
            "baseline_receivable_delay_hours": self.baseline_receivable_delay_hours,
            "baseline_payable_delay_hours": self.baseline_payable_delay_hours,
            "baseline_cash_gap_hours": self.baseline_cash_gap_hours,
        }


@dataclass(frozen=True)
class ProjectedEconomics:
    projected_service_cost_eur: float
    projected_action_cost_eur: float
    projected_total_cost_eur: float
    projected_margin_eur: float
    projected_margin_pct: float
    projected_receivable_delay_hours: int
    projected_payable_delay_hours: int
    projected_cash_gap_hours: int
    projected_net_working_capital_eur: float
    current_cash_balance_eur: float
    current_accounts_receivable_eur: float
    current_accounts_payable_eur: float
    current_net_working_capital_eur: float
    bankruptcy_threshold_eur: float
    cost_policy_version: str

    def as_guardrail_context(self) -> dict[str, float | int]:
        return {
            "projected_service_cost_eur": self.projected_service_cost_eur,
            "projected_action_cost_eur": self.projected_action_cost_eur,
            "projected_total_cost_eur": self.projected_total_cost_eur,
            "projected_margin_eur": self.projected_margin_eur,
            "projected_margin_pct": self.projected_margin_pct,
            "projected_receivable_delay_hours": self.projected_receivable_delay_hours,
            "projected_payable_delay_hours": self.projected_payable_delay_hours,
            "projected_cash_gap_hours": self.projected_cash_gap_hours,
            "projected_net_working_capital_eur": self.projected_net_working_capital_eur,
            "current_cash_balance_eur": self.current_cash_balance_eur,
            "current_accounts_receivable_eur": self.current_accounts_receivable_eur,
            "current_accounts_payable_eur": self.current_accounts_payable_eur,
            "current_net_working_capital_eur": self.current_net_working_capital_eur,
            "bankruptcy_threshold_eur": self.bankruptcy_threshold_eur,
            "cost_policy_version": self.cost_policy_version,
        }


@dataclass(frozen=True)
class CostPolicy:
    version: str = "waste-company-cost-policy-v1"
    starting_cash_eur: float = DEFAULT_STARTING_CASH_EUR
    daily_overhead_eur: float = DEFAULT_DAILY_OVERHEAD_EUR
    bankruptcy_burn_multiple: float = DEFAULT_BANKRUPTCY_BURN_MULTIPLE
    overflow_penalty_eur: float = 350.0
    contamination_risk_surcharge_eur: float = 10.0
    hazardous_flag_surcharge_eur: float = 28.0
    min_margin_pct_for_approval: float = DEFAULT_MIN_MARGIN_PCT_FOR_APPROVAL
    min_margin_pct_for_auto_approve: float = DEFAULT_MIN_MARGIN_PCT_FOR_AUTO_APPROVE
    max_cash_gap_hours: int = DEFAULT_MAX_CASH_GAP_HOURS
    quote_floor_surcharge_eur: float = 8.0
    quote_margin_multiplier: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_QUOTE_MARGIN_MULTIPLIER))
    service_base_cost_eur: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SERVICE_BASE_COST_EUR))
    service_cost_per_m3_eur: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SERVICE_COST_PER_M3_EUR))
    service_window_price_multiplier: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SERVICE_WINDOW_PRICE_MULTIPLIER))
    service_window_cost_multiplier: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SERVICE_WINDOW_COST_MULTIPLIER))
    customer_payment_delay_hours: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_PAYMENT_DELAY_HOURS))
    vendor_payment_delay_hours: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_VENDOR_PAYMENT_DELAY_HOURS))
    hazardous_vendor_payment_delay_hours: int = 12

    @classmethod
    def from_json_file(cls, path: str | Path) -> "CostPolicy":
        payload = json.loads(Path(path).read_text())
        if not isinstance(payload, dict):
            raise ValueError("Cost policy JSON must be a JSON object.")
        merged = cls._merge_payload(payload)
        cls._validate_required_mapping_keys(merged)
        return cls(**merged)

    @classmethod
    def _merge_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        merged = asdict(cls())
        mapping_fields = {
            "quote_margin_multiplier",
            "service_base_cost_eur",
            "service_cost_per_m3_eur",
            "service_window_price_multiplier",
            "service_window_cost_multiplier",
            "customer_payment_delay_hours",
            "vendor_payment_delay_hours",
        }
        for key, value in payload.items():
            if key in mapping_fields:
                if not isinstance(value, dict):
                    raise ValueError(f"Cost policy field '{key}' must be a JSON object.")
                merged[key].update(value)
                continue
            merged[key] = value
        return merged

    @classmethod
    def _validate_required_mapping_keys(cls, merged: dict[str, object]) -> None:
        defaults = asdict(cls())
        mapping_fields = {
            "quote_margin_multiplier",
            "service_base_cost_eur",
            "service_cost_per_m3_eur",
            "service_window_price_multiplier",
            "service_window_cost_multiplier",
            "customer_payment_delay_hours",
            "vendor_payment_delay_hours",
        }
        for field_name in mapping_fields:
            field_value = merged.get(field_name)
            if not isinstance(field_value, dict):
                raise ValueError(f"Cost policy field '{field_name}' must be a JSON object.")
            missing_keys = sorted(set(defaults[field_name]) - set(field_value))
            if missing_keys:
                raise ValueError(
                    f"Cost policy field '{field_name}' is missing required keys: {missing_keys}"
                )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "starting_cash_eur": self.starting_cash_eur,
            "daily_overhead_eur": self.daily_overhead_eur,
            "bankruptcy_burn_multiple": self.bankruptcy_burn_multiple,
            "overflow_penalty_eur": self.overflow_penalty_eur,
            "min_margin_pct_for_approval": self.min_margin_pct_for_approval,
            "min_margin_pct_for_auto_approve": self.min_margin_pct_for_auto_approve,
            "max_cash_gap_hours": self.max_cash_gap_hours,
            "customer_payment_delay_hours": dict(self.customer_payment_delay_hours),
            "vendor_payment_delay_hours": dict(self.vendor_payment_delay_hours),
            "hazardous_vendor_payment_delay_hours": self.hazardous_vendor_payment_delay_hours,
        }


def load_cost_policy(path: str | Path | None = None) -> CostPolicy:
    if path is None:
        return CostPolicy()
    return CostPolicy.from_json_file(path)


def estimate_service_cost(
    *,
    policy: CostPolicy,
    waste_type: WasteType,
    quantity_m3: float,
    service_window: ServiceWindow,
    contamination_risk: bool,
    hazardous_flag: bool,
) -> float:
    subtotal = policy.service_base_cost_eur[waste_type.value] + (
        policy.service_cost_per_m3_eur[waste_type.value] * quantity_m3
    )
    subtotal *= policy.service_window_cost_multiplier[service_window.value]
    if contamination_risk:
        subtotal += policy.contamination_risk_surcharge_eur
    if hazardous_flag:
        subtotal += policy.hazardous_flag_surcharge_eur
    return round(subtotal, 2)


def estimate_payment_delay_hours(*, policy: CostPolicy, service_window: ServiceWindow) -> int:
    return int(policy.customer_payment_delay_hours[service_window.value])


def estimate_vendor_payment_delay_hours(
    *,
    policy: CostPolicy,
    service_window: ServiceWindow,
    hazardous_flag: bool,
) -> int:
    if hazardous_flag:
        return int(policy.hazardous_vendor_payment_delay_hours)
    return int(policy.vendor_payment_delay_hours[service_window.value])


def bankruptcy_threshold_eur(*, policy: CostPolicy) -> float:
    return -policy.bankruptcy_burn_multiple * policy.daily_overhead_eur


def compute_dynamic_early_empty_cost(
    *,
    base_cost: float,
    fill_ratio: float,
    hours_to_pickup: float,
    overflow_penalty_eur: float,
) -> float:
    """Compute dynamic early-empty cost based on container state.

    Low fill → expensive (wasteful to empty), high fill → discounted (prevent overflow).
    Near scheduled pickup → expensive (just wait), far from pickup → cheaper.
    Cost is capped at the overflow penalty so it's always rational to empty vs overflow.
    """
    # Fill urgency: 1.0 at 0% fill → 0.5 at 100% fill
    fill_factor = 1.0 - (fill_ratio * 0.5)

    # Pickup proximity: expensive if pickup is soon, cheaper if far away
    proximity_factor = max(0.3, 1.0 - (hours_to_pickup / 48))

    # Overflow risk: heavy discount when overflow is imminent
    overflow_discount = 1.0
    if fill_ratio >= 0.9:
        overflow_discount = 0.3
    elif fill_ratio >= 0.75:
        overflow_discount = 0.6

    dynamic_cost = base_cost * fill_factor * proximity_factor * overflow_discount
    # Cap at overflow penalty so emptying is always cheaper than overflowing
    return round(max(min(dynamic_cost, overflow_penalty_eur * 0.9), 5.0), 2)


def project_order_economics(
    *,
    policy: CostPolicy,
    offered_price_eur: float,
    waste_type: WasteType,
    quantity_m3: float,
    service_window: ServiceWindow,
    contamination_risk: bool,
    hazardous_flag: bool,
) -> BaselineOrderEconomics:
    baseline_service_cost = estimate_service_cost(
        policy=policy,
        waste_type=waste_type,
        quantity_m3=quantity_m3,
        service_window=service_window,
        contamination_risk=contamination_risk,
        hazardous_flag=hazardous_flag,
    )
    receivable_delay = estimate_payment_delay_hours(policy=policy, service_window=service_window)
    payable_delay = estimate_vendor_payment_delay_hours(
        policy=policy,
        service_window=service_window,
        hazardous_flag=hazardous_flag,
    )
    baseline_margin = round(offered_price_eur - baseline_service_cost, 2)
    baseline_margin_pct = 0.0 if offered_price_eur <= 0 else round(baseline_margin / offered_price_eur, 4)
    return BaselineOrderEconomics(
        customer_price_eur=round(offered_price_eur, 2),
        baseline_service_cost_eur=round(baseline_service_cost, 2),
        baseline_total_cost_eur=round(baseline_service_cost, 2),
        baseline_margin_eur=baseline_margin,
        baseline_margin_pct=baseline_margin_pct,
        baseline_receivable_delay_hours=receivable_delay,
        baseline_payable_delay_hours=payable_delay,
        baseline_cash_gap_hours=max(receivable_delay - payable_delay, 0),
    )


def project_action_economics(
    *,
    policy: CostPolicy,
    offered_price_eur: float,
    waste_type: WasteType,
    quantity_m3: float,
    service_window: ServiceWindow,
    contamination_risk: bool,
    hazardous_flag: bool,
    bot_action: str,
    action_payload: dict | None,
    current_cash_balance_eur: float,
    accounts_receivable_eur: float = 0.0,
    accounts_payable_eur: float = 0.0,
) -> ProjectedEconomics:
    payload = action_payload or {}
    projected_service_cost = estimate_service_cost(
        policy=policy,
        waste_type=waste_type,
        quantity_m3=quantity_m3,
        service_window=service_window,
        contamination_risk=contamination_risk,
        hazardous_flag=hazardous_flag,
    )
    projected_action_cost = 0.0
    if bot_action == "rent_container":
        rental_cost = float(payload.get("extra_rental_cost_eur", 0.0))
        setup_cost = min(120.0, round(rental_cost * 0.25, 2))
        projected_action_cost = rental_cost + setup_cost
    elif bot_action == "schedule_early_empty":
        projected_action_cost = float(payload.get("early_empty_cost_eur", 0.0))

    projected_total_cost = round(projected_service_cost + projected_action_cost, 2)
    projected_margin = round(offered_price_eur - projected_total_cost, 2)
    projected_margin_pct = 0.0 if offered_price_eur <= 0 else round(projected_margin / offered_price_eur, 4)
    receivable_delay = estimate_payment_delay_hours(policy=policy, service_window=service_window)
    payable_delay = estimate_vendor_payment_delay_hours(
        policy=policy,
        service_window=service_window,
        hazardous_flag=hazardous_flag,
    )
    projected_cash_gap_hours = max(receivable_delay - payable_delay, 0)
    projected_nwc = round(
        current_cash_balance_eur + accounts_receivable_eur + offered_price_eur - accounts_payable_eur - projected_total_cost,
        2,
    )
    current_nwc = round(current_cash_balance_eur + accounts_receivable_eur - accounts_payable_eur, 2)
    return ProjectedEconomics(
        projected_service_cost_eur=round(projected_service_cost, 2),
        projected_action_cost_eur=round(projected_action_cost, 2),
        projected_total_cost_eur=projected_total_cost,
        projected_margin_eur=projected_margin,
        projected_margin_pct=projected_margin_pct,
        projected_receivable_delay_hours=receivable_delay,
        projected_payable_delay_hours=payable_delay,
        projected_cash_gap_hours=projected_cash_gap_hours,
        projected_net_working_capital_eur=projected_nwc,
        current_cash_balance_eur=round(current_cash_balance_eur, 2),
        current_accounts_receivable_eur=round(accounts_receivable_eur, 2),
        current_accounts_payable_eur=round(accounts_payable_eur, 2),
        current_net_working_capital_eur=current_nwc,
        bankruptcy_threshold_eur=round(bankruptcy_threshold_eur(policy=policy), 2),
        cost_policy_version=policy.version,
    )
