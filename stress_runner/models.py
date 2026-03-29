"""Run-level result models for waste-company evaluation runs."""

from datetime import datetime

from pydantic import BaseModel, Field


class OrderTrace(BaseModel):
    order_id: str
    waste_type: str
    expected_action: str
    expected_outcome: str
    actions: list[dict] = Field(default_factory=list)
    final_outcome: str | None = None
    error: str | None = None
    duration_ms: float | None = None


class StressRunResult(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    seed: int
    total_orders: int = 0
    approve_count: int = 0
    ask_for_approval_count: int = 0
    reject_count: int = 0
    error_count: int = 0
    path_accuracy: float = 0.0
    traces: list[OrderTrace] = Field(default_factory=list)
