"""Governed action contract — every bot action must go through this."""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class ActionOutcome(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PENDING = "PENDING"
    TIMED_OUT = "TIMED_OUT"
    ERROR = "ERROR"


class GovernedBotAction(BaseModel):
    """An action proposed by the bot, before Unreal Objects evaluation."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_name: str
    case_id: str
    action_payload: dict = Field(default_factory=dict)
    business_reason: str
    user_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class ActionResult(BaseModel):
    """Result after Unreal Objects evaluation + optional execution."""

    action_id: str
    case_id: str
    request_id: str  # Unreal Objects request_id from /v1/decide
    outcome: ActionOutcome
    matched_rules: list[str] = Field(default_factory=list)
    executed: bool = False
    execution_result: dict | None = None
    resolved_by: str | None = None  # human reviewer ID if manually approved/rejected
    resolved_at: datetime | None = None
