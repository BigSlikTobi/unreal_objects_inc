"""Governance client — sends bot actions to Unreal Objects for evaluation."""

import httpx

from .models import GovernedBotAction, ActionResult, ActionOutcome


class GovernanceClient:
    """Thin HTTP client wrapping Unreal Objects Decision Center APIs."""

    def __init__(
        self,
        decision_center_url: str = "http://127.0.0.1:8002",
        timeout: float = 30.0,
    ):
        self.base_url = decision_center_url.rstrip("/")
        self.timeout = timeout

    async def evaluate(
        self,
        action: GovernedBotAction,
        group_id: str,
        context: dict,
    ) -> ActionResult:
        """Submit a governed action to POST /v1/decide and return the result."""
        payload = {
            "request_description": f"{action.action_name}: {action.business_reason}",
            "group_id": group_id,
            "context": context,
        }
        if action.user_id:
            payload["agent_id"] = action.user_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/decide", json=payload)
            resp.raise_for_status()
            data = resp.json()

        outcome_map = {
            "APPROVE": ActionOutcome.APPROVED,
            "REJECT": ActionOutcome.REJECTED,
            "ASK_FOR_APPROVAL": ActionOutcome.APPROVAL_REQUIRED,
            "APPROVED": ActionOutcome.APPROVED,
            "REJECTED": ActionOutcome.REJECTED,
            "APPROVAL_REQUIRED": ActionOutcome.APPROVAL_REQUIRED,
        }
        outcome = data.get("outcome") or data.get("decision")

        return ActionResult(
            action_id=action.action_id,
            case_id=action.case_id,
            request_id=data["request_id"],
            outcome=outcome_map.get(outcome, ActionOutcome.ERROR),
            matched_rules=data.get("matched_rules", []),
        )

    async def get_pending(self) -> list[dict]:
        """Fetch all pending approval items."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/v1/pending")
            resp.raise_for_status()
            return resp.json()

    async def submit_approval(
        self,
        request_id: str,
        approved: bool,
        reviewer: str = "operator",
    ) -> dict:
        """Approve or reject a pending decision."""
        payload = {"approved": approved, "approver": reviewer}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/decide/{request_id}/approve",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_chain(self, request_id: str) -> dict:
        """Fetch the full decision chain for a request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/v1/logs/chains/{request_id}"
            )
            resp.raise_for_status()
            return resp.json()
