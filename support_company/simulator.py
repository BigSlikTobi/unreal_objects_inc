"""Waste-operations simulator with mixed LLM and deterministic generation."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .generator import (
    expected_action_for_order,
    expected_outcome_for_order,
    generate_batch,
    generate_initial_containers,
    generate_order_event,
)
from .cost_policy import CostPolicy
from .models import (
    CompanyOperationSnapshot,
    DisposalOrder,
    GeneratedScenario,
    GeneratedScenarioBatch,
)


DEFAULT_LLM_MODEL = "gpt-5.4-mini-2026-03-17"


def load_local_env() -> None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() and key.strip() not in os.environ:
                os.environ[key.strip()] = value.strip().strip("'").strip('"')
        return


@dataclass
class ScenarioGenerationConfig:
    count: int = 24
    seed: int = 42
    mode: str = "mixed"
    prefer_llm: bool | None = None
    allow_template_fallback: bool = True
    model: str = DEFAULT_LLM_MODEL
    api_key: str | None = None
    cost_policy: CostPolicy | None = None


class OpenAIWasteScenarioGenerator:
    """LLM-backed generator for realistic waste-disposal orders."""

    def __init__(self, model: str = DEFAULT_LLM_MODEL, api_key: str | None = None):
        load_local_env()
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, count: int, seed: int) -> list[GeneratedScenario]:
        if not self.configured:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are simulating a modern waste-management company. "
                "Generate realistic disposal orders, operational context, and expected autonomous bot actions. "
                "Return valid JSON only."
            ),
            input=(
                f"Generate {count} realistic waste-order scenarios using deterministic seed {seed}. "
                "Each scenario must include operational context, a raw disposal-order event, a derived disposal order, "
                "the expected bot action, and the expected Unreal Objects outcome. "
                "Use only these enums exactly:\n"
                "waste type: residual, recycling, paper, glass, organic, hazardous\n"
                "priority: standard, urgent\n"
                "service window: same_day, next_day, scheduled\n"
                "event source: customer, operations, market\n"
                "event type: disposal_order_request, emptying_due, overflow_alert, cost_pressure\n"
                "expected action: accept_and_route, reject_order, rent_container, schedule_early_empty\n"
                "expected outcome: APPROVE, ASK_FOR_APPROVAL, REJECT\n"
                "Keep customer messages short and realistic. "
                "Return JSON with top-level key 'scenarios'."
            ),
        )
        payload = json.loads(response.output_text)
        return GeneratedScenarioBatch.model_validate(payload).scenarios


def generate_scenarios(config: ScenarioGenerationConfig) -> list[GeneratedScenario]:
    mode = _resolve_generation_mode(config)
    if mode == "template":
        return generate_template_scenarios(count=config.count, seed=config.seed, cost_policy=config.cost_policy)
    if mode == "llm":
        return _generate_llm_first_scenarios(config)
    if mode == "mixed":
        return _generate_mixed_scenarios(config)
    raise ValueError(f"Unsupported scenario generation mode: {mode}")


def _resolve_generation_mode(config: ScenarioGenerationConfig) -> str:
    if config.prefer_llm is not None:
        return "llm" if config.prefer_llm else "template"
    return config.mode


def _generate_llm_first_scenarios(config: ScenarioGenerationConfig) -> list[GeneratedScenario]:
    llm = OpenAIWasteScenarioGenerator(model=config.model, api_key=config.api_key)
    if llm.configured:
        try:
            return llm.generate(config.count, config.seed)
        except Exception:
            if not config.allow_template_fallback:
                raise
    elif not config.allow_template_fallback:
        raise RuntimeError("OPENAI_API_KEY is required when template fallback is disabled")
    return generate_template_scenarios(count=config.count, seed=config.seed, cost_policy=config.cost_policy)


def _generate_mixed_scenarios(config: ScenarioGenerationConfig) -> list[GeneratedScenario]:
    llm_count, template_count = _split_mixed_counts(count=config.count, seed=config.seed)
    scenarios: list[GeneratedScenario] = []
    llm = OpenAIWasteScenarioGenerator(model=config.model, api_key=config.api_key)

    if llm_count > 0:
        if llm.configured:
            try:
                scenarios.extend(llm.generate(llm_count, config.seed))
            except Exception:
                if not config.allow_template_fallback:
                    raise
                template_count += llm_count
        elif not config.allow_template_fallback:
            raise RuntimeError("OPENAI_API_KEY is required when template fallback is disabled")
        else:
            template_count += llm_count

    if template_count > 0:
        scenarios.extend(
            generate_template_scenarios(
                count=template_count,
                seed=config.seed + 10_000,
                cost_policy=config.cost_policy,
            )
        )

    random.Random(config.seed).shuffle(scenarios)
    return scenarios


def _split_mixed_counts(count: int, seed: int) -> tuple[int, int]:
    if count <= 0:
        return 0, 0
    if count == 1:
        llm_count = 1 if seed % 2 == 0 else 0
        return llm_count, count - llm_count
    llm_count = max(1, count // 2)
    return llm_count, count - llm_count


def generate_template_scenarios(
    count: int = 24,
    seed: int = 42,
    cost_policy: CostPolicy | None = None,
) -> list[GeneratedScenario]:
    rng = random.Random(seed)
    base_time = datetime.now(UTC)
    orders = generate_batch(count=count, seed=seed, policy=cost_policy)
    scenarios: list[GeneratedScenario] = []

    for idx, order in enumerate(orders):
        occurred_at = base_time - timedelta(minutes=idx * rng.randint(5, 30))
        operations = CompanyOperationSnapshot(
            operating_window=rng.choice(["morning_route", "midday_peak", "afternoon_turn", "night_yard"]),
            demand_level=rng.choice(["steady", "busy", "surging"]),
            depot_load=rng.choice(["balanced", "tight", "strained"]),
            business_note=rng.choice(
                [
                    "Container utilization is under active review.",
                    "Operations is prioritizing margin-positive loads this shift.",
                    "Hazardous handling capacity is under tighter control today.",
                ]
            ),
        )
        event = generate_order_event(order, operations, occurred_at)
        scenarios.append(
            GeneratedScenario(
                operations=operations,
                event=event,
                order=order.model_copy(
                    update={
                        "created_at": occurred_at,
                        "source_event_id": event.event_id,
                        "source_event_type": event.event_type,
                        "source_event_source": event.source,
                        "source_event_summary": event.summary,
                    }
                ),
                expected_action=expected_action_for_order(order),
                expected_outcome=expected_outcome_for_order(order),
            )
        )

    return scenarios


def generate_container_fleet(seed: int = 42, now: datetime | None = None):
    return generate_initial_containers(seed=seed, now=now)


def generate_order_batch(
    count: int = 50,
    seed: int = 42,
    cost_policy: CostPolicy | None = None,
) -> list[DisposalOrder]:
    return generate_batch(count=count, seed=seed, policy=cost_policy)
