"""Tests for waste-operations simulation."""

from support_company.generator import generate_initial_containers
from support_company.models import DisposalOrder, ExpectedPath, GeneratedScenarioBatch, OrderPriority, ServiceWindow, WasteType
from support_company.simulator import (
    OpenAIWasteScenarioGenerator,
    ScenarioGenerationConfig,
    generate_scenarios,
    generate_template_scenarios,
)


def test_template_scenarios_include_operations_and_events():
    scenarios = generate_template_scenarios(count=8, seed=42)

    assert len(scenarios) == 8
    assert scenarios[0].operations.demand_level in {"steady", "busy", "surging"}
    assert scenarios[0].event.summary
    assert scenarios[0].order.source_event_id == scenarios[0].event.event_id
    assert scenarios[0].order.source_event_type == scenarios[0].event.event_type


def test_generate_scenarios_falls_back_without_api_key():
    scenarios = generate_scenarios(
        ScenarioGenerationConfig(
            count=5,
            seed=7,
            mode="llm",
            allow_template_fallback=True,
            api_key="",
        )
    )

    assert len(scenarios) == 5
    assert all(s.order.source_event_summary for s in scenarios)


def test_generated_batch_schema_accepts_template_output():
    scenarios = generate_template_scenarios(count=3, seed=11)
    batch = GeneratedScenarioBatch.model_validate({"scenarios": [s.model_dump(mode="json") for s in scenarios]})
    assert len(batch.scenarios) == 3


def test_expected_outcomes_cover_reject_and_approve():
    scenarios = generate_template_scenarios(count=40, seed=12)
    outcomes = {scenario.expected_outcome for scenario in scenarios}
    assert ExpectedPath.REJECT in outcomes
    assert ExpectedPath.APPROVE in outcomes


def test_initial_container_fleet_contains_hazardous_capacity():
    containers = generate_initial_containers(seed=42)
    waste_types = {container.waste_type for container in containers}
    assert WasteType.HAZARDOUS in waste_types


def test_generate_scenarios_mixed_mode_blends_llm_and_template(monkeypatch):
    llm_only = generate_template_scenarios(count=2, seed=101)
    for scenario in llm_only:
        scenario.order.title = f"LLM {scenario.order.title}"

    monkeypatch.setattr(OpenAIWasteScenarioGenerator, "configured", property(lambda self: True))
    monkeypatch.setattr(OpenAIWasteScenarioGenerator, "generate", lambda self, count, seed: llm_only[:count])

    scenarios = generate_scenarios(
        ScenarioGenerationConfig(
            count=4,
            seed=12,
            mode="mixed",
            allow_template_fallback=True,
            api_key="fake-key",
        )
    )

    assert len(scenarios) == 4
    assert any(s.order.title.startswith("LLM ") for s in scenarios)
    assert any(not s.order.title.startswith("LLM ") for s in scenarios)
