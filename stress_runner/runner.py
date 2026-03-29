"""Core waste-run orchestrator for batch evaluation."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime

from bot_adapter.governance import GovernanceClient
from bot_adapter.models import GovernedBotAction
from bot_adapter.rule_loader import load_rule_pack
from support_company.models import DisposalOrder
from support_company.simulator import DEFAULT_LLM_MODEL, ScenarioGenerationConfig, generate_scenarios

from .models import OrderTrace, StressRunResult


EXPECTED_PATH_TO_OUTCOME = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "ASK_FOR_APPROVAL": "APPROVAL_REQUIRED",
}


async def _process_order(order: DisposalOrder, expected_action: str, expected_outcome: str, group_id: str, gov: GovernanceClient) -> OrderTrace:
    start = time.monotonic()
    trace = OrderTrace(
        order_id=order.order_id,
        waste_type=order.declared_waste_type.value,
        expected_action=expected_action,
        expected_outcome=expected_outcome,
    )
    try:
        action_payload = {"target_waste_type": order.declared_waste_type.value, "route_quantity_m3": order.quantity_m3}
        action = GovernedBotAction(
            action_name=expected_action,
            case_id=order.order_id,
            action_payload=action_payload,
            business_reason=f"Handle waste order {order.order_id}",
        )
        result = await gov.evaluate(action=action, group_id=group_id, context=order.to_evaluation_context(bot_action=expected_action, action_payload=action_payload))
        trace.actions.append(
            {
                "action_id": action.action_id,
                "action_name": action.action_name,
                "request_id": result.request_id,
                "outcome": result.outcome.value,
                "matched_rules": result.matched_rules,
            }
        )
        trace.final_outcome = result.outcome.value
    except Exception as exc:
        trace.error = str(exc)
        trace.final_outcome = "ERROR"
    trace.duration_ms = (time.monotonic() - start) * 1000
    return trace


async def run_stress_test(
    rule_pack_path: str,
    case_count: int = 50,
    seed: int = 42,
    concurrency: int = 5,
    rule_engine_url: str = "http://127.0.0.1:8001",
    decision_center_url: str = "http://127.0.0.1:8002",
    generator_mode: str = "mixed",
    llm_model: str = DEFAULT_LLM_MODEL,
    allow_template_fallback: bool = True,
) -> StressRunResult:
    run_id = str(uuid.uuid4())
    started_at = datetime.now()
    group_id = await load_rule_pack(rule_pack_path, rule_engine_url=rule_engine_url)

    scenarios = generate_scenarios(
        ScenarioGenerationConfig(
            count=case_count,
            seed=seed,
            mode=generator_mode,
            allow_template_fallback=allow_template_fallback,
            model=llm_model,
        )
    )

    gov = GovernanceClient(decision_center_url=decision_center_url)
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(order: DisposalOrder, expected_action: str, expected_outcome: str):
        async with semaphore:
            return await _process_order(order, expected_action, expected_outcome, group_id, gov)

    traces = await asyncio.gather(
        *[
            bounded(scenario.order, scenario.expected_action.value, scenario.expected_outcome.value)
            for scenario in scenarios
        ]
    )

    result = StressRunResult(
        run_id=run_id,
        started_at=started_at,
        finished_at=datetime.now(),
        seed=seed,
        total_orders=len(traces),
        traces=list(traces),
    )

    correct = 0
    for trace in traces:
        if trace.final_outcome == "APPROVED":
            result.approve_count += 1
        elif trace.final_outcome == "APPROVAL_REQUIRED":
            result.ask_for_approval_count += 1
        elif trace.final_outcome == "REJECTED":
            result.reject_count += 1
        else:
            result.error_count += 1
        if trace.final_outcome == EXPECTED_PATH_TO_OUTCOME.get(trace.expected_outcome):
            correct += 1
    result.path_accuracy = (correct / len(traces) * 100) if traces else 0.0
    return result
