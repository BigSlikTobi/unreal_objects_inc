#!/usr/bin/env python3
"""Load the current waste-company rule pack into the local Unreal Objects Rule Engine."""

from __future__ import annotations

import json
from pathlib import Path
from urllib import request


BASE_URL = "http://127.0.0.1:8001"
RULE_PACK_PATH = Path(__file__).resolve().parent.parent / "rule_packs" / "support_company.json"


def post_json(url: str, payload: dict) -> dict:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    rule_pack = json.loads(RULE_PACK_PATH.read_text())
    group = post_json(
        f"{BASE_URL}/v1/groups",
        {
            "name": rule_pack["name"],
            "description": rule_pack["description"],
        },
    )
    group_id = group["id"]

    for rule in rule_pack["rules"]:
        post_json(f"{BASE_URL}/v1/groups/{group_id}/rules", rule)

    print(group_id)


if __name__ == "__main__":
    main()
