"""Loads rule packs into the Unreal Objects Rule Engine."""

import json
from pathlib import Path
import httpx


async def load_rule_pack(
    rule_pack_path: str | Path,
    rule_engine_url: str = "http://127.0.0.1:8001",
    timeout: float = 30.0,
) -> str:
    """Load a rule pack JSON file into the Rule Engine.

    Returns the created group_id.
    """
    pack = json.loads(Path(rule_pack_path).read_text())

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Create the group
        group_resp = await client.post(
            f"{rule_engine_url}/v1/groups",
            json={"name": pack["name"], "description": pack.get("description", "")},
        )
        group_resp.raise_for_status()
        group_id = group_resp.json()["id"]

        # Create each rule
        for rule in pack["rules"]:
            rule_resp = await client.post(
                f"{rule_engine_url}/v1/groups/{group_id}/rules",
                json=rule,
            )
            rule_resp.raise_for_status()

    return group_id
