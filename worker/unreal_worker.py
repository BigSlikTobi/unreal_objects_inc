#!/usr/bin/env python3
"""Autonomous waste-disposal worker for unreal_objects_inc.

Polls the company API for open orders, decides the best action,
evaluates it against Unreal Objects guardrails via the Decision Center,
and submits the result back to the company.

Processes multiple orders concurrently using a thread pool.
Context variables match the rule pack in rule_packs/support_company.json.
"""

import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Configuration (env-overridable for cloud deployment) ───────────
COMPANY_BASE = os.environ.get("COMPANY_API_URL", "http://192.168.178.21:8010")
DECISION_CENTER = os.environ.get("DECISION_CENTER_URL", "http://192.168.178.21:8002")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")
BOT_ID = os.environ.get("BOT_ID", "deborahbot3000")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "6"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))


# ── HTTP helper ────────────────────────────────────────────────────

def http_json(url, method="GET", data=None, timeout=20, extra_headers=None):
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ── Company API wrappers ───────────────────────────────────────────

def fetch_open_orders():
    return http_json(f"{COMPANY_BASE}/api/v1/orders?status=open").get("orders", [])

def fetch_containers():
    return http_json(f"{COMPANY_BASE}/api/v1/containers").get("containers", [])

def fetch_group_id():
    """Read the live group_id from the company status or rules endpoint."""
    status = http_json(f"{COMPANY_BASE}/api/v1/status")
    gid = status.get("group_id")
    if gid:
        return gid
    # Fallback: extract from rules endpoint
    resp = http_json(f"{COMPANY_BASE}/api/v1/rules")
    if isinstance(resp, dict):
        # Try groups list first
        groups = resp.get("groups", [])
        if groups:
            return groups[0].get("id")
        # Try group_id on individual rules
        rules = resp.get("rules", [])
        if rules:
            return rules[0].get("group_id")
    elif isinstance(resp, list) and resp:
        return resp[0].get("group_id")
    return None

def claim_order(order_id):
    return http_json(f"{COMPANY_BASE}/api/v1/orders/{order_id}/claim", method="POST", data={"bot_id": BOT_ID})

def submit_result(order_id, payload):
    return http_json(f"{COMPANY_BASE}/api/v1/orders/{order_id}/result", method="POST", data=payload)


# ── Guardrail evaluation via Decision Center ───────────────────────

def evaluate_action(description, context, group_id):
    payload = {
        "request_description": description,
        "context": context,
        "group_id": group_id,
        "user_id": BOT_ID,
    }
    extra = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else None
    return http_json(f"{DECISION_CENTER}/v1/decide", method="POST", data=payload, extra_headers=extra)


# ── Decision logic ─────────────────────────────────────────────────

def remaining_capacity(container):
    return container["capacity_m3"] - container["fill_level_m3"]

def rank_orders(orders):
    """Sort orders by profitability (EUR/m3), non-hazardous first."""
    def sort_key(o):
        haz_penalty = 0 if o["declared_waste_type"] != "hazardous" else -10000
        return haz_penalty + o["offered_price_eur"] / max(o["quantity_m3"], 0.1)
    return sorted(orders, key=sort_key, reverse=True)

def decide_action(order, containers):
    """Choose the best action for an order.

    Returns (action_name, description, guardrail_context, action_payload).
    Context variables match rule_packs/support_company.json datapoints.
    """
    wtype = order["declared_waste_type"]
    qty = order["quantity_m3"]
    price = order["offered_price_eur"]
    matching = [c for c in containers if c["waste_type"] == wtype]

    # ── 1. Accept & route into existing capacity ──────────────────
    for c in sorted(matching, key=remaining_capacity, reverse=True):
        avail = remaining_capacity(c)
        if qty <= avail:
            desc = (
                f"Route {qty} m3 of {wtype} into {c['label']} "
                f"(available: {avail:.1f} m3, offered: {price:.2f} EUR)."
            )
            ctx = {
                "declared_waste_type": wtype,
                "target_waste_type": c["waste_type"],
                "bot_action": "accept_and_route",
                "quantity_m3": qty,
                "route_quantity_m3": qty,
                "available_capacity_m3": avail,
                "offered_price_eur": price,
                "extra_rental_cost_eur": 0,
                "early_empty_cost_eur": 0,
                "added_capacity_m3": 0,
            }
            payload = {
                "target_container_id": c["container_id"],
                "target_waste_type": wtype,
                "available_capacity_m3": avail,
                "route_quantity_m3": qty,
            }
            return "accept_and_route", desc, ctx, payload

    # ── 2. Early empty if container exists but is too full ────────
    for c in matching:
        early_cost = c["early_empty_cost_eur"]
        full_cap = c["capacity_m3"]
        if qty <= full_cap and price > early_cost:
            desc = (
                f"Early-empty {c['label']} (cost: {early_cost:.2f} EUR) "
                f"then route {qty} m3 of {wtype} (offered: {price:.2f} EUR)."
            )
            ctx = {
                "declared_waste_type": wtype,
                "target_waste_type": c["waste_type"],
                "bot_action": "schedule_early_empty",
                "quantity_m3": qty,
                "route_quantity_m3": qty,
                "available_capacity_m3": full_cap,
                "offered_price_eur": price,
                "extra_rental_cost_eur": 0,
                "early_empty_cost_eur": early_cost,
                "added_capacity_m3": 0,
            }
            payload = {
                "target_container_id": c["container_id"],
                "early_empty_cost_eur": early_cost,
                "available_capacity_m3": full_cap,
                "route_quantity_m3": qty,
            }
            return "schedule_early_empty", desc, ctx, payload

    # ── 3. Rent new container if economically sensible ────────────
    rental_capacity = min(max(qty * 1.5, 8.0), 12.0)
    rental_cost = 420.0
    if qty <= rental_capacity and price > rental_cost * 0.4:
        desc = (
            f"Rent {wtype} container ({rental_capacity:.1f} m3, "
            f"cost: {rental_cost:.2f} EUR) and route {qty} m3 (offered: {price:.2f} EUR)."
        )
        ctx = {
            "declared_waste_type": wtype,
            "target_waste_type": wtype,
            "bot_action": "rent_container",
            "quantity_m3": qty,
            "route_quantity_m3": qty,
            "available_capacity_m3": rental_capacity,
            "offered_price_eur": price,
            "extra_rental_cost_eur": rental_cost,
            "early_empty_cost_eur": 0,
            "added_capacity_m3": rental_capacity,
        }
        payload = {
            "target_waste_type": wtype,
            "added_capacity_m3": rental_capacity,
            "extra_rental_cost_eur": rental_cost,
            "route_quantity_m3": qty,
        }
        return "rent_container", desc, ctx, payload

    # ── 4. Reject ─────────────────────────────────────────────────
    reason = (
        f"No viable capacity for {qty} m3 of {wtype}; "
        f"offered price ({price:.2f} EUR) does not justify rental."
    )
    ctx = {
        "declared_waste_type": wtype,
        "target_waste_type": wtype,
        "bot_action": "reject_order",
        "quantity_m3": qty,
        "route_quantity_m3": 0,
        "available_capacity_m3": 0,
        "offered_price_eur": price,
        "extra_rental_cost_eur": 0,
        "early_empty_cost_eur": 0,
        "added_capacity_m3": 0,
    }
    payload = {"reason": reason}
    return "reject_order", f"Reject: {reason}", ctx, payload


def _format_guardrail_reasoning(eval_result):
    """Extract human-readable guardrail reasoning from matched_details."""
    details = eval_result.get("matched_details", [])
    if not details:
        return "No guardrail rules triggered."
    lines = []
    for d in details:
        name = d.get("rule_name", "Unknown rule")
        expr = d.get("trigger_expression", "")
        lines.append(f"[{name}] {expr}")
    return " | ".join(lines)

def _describe_action_reasoning(action, order, action_payload, containers_snapshot=None):
    """Explain why the bot chose this action in business terms."""
    wtype = order["declared_waste_type"]
    qty = order["quantity_m3"]
    price = order["offered_price_eur"]

    if action == "accept_and_route":
        cid = action_payload.get("target_container_id", "?")[:8]
        avail = action_payload.get("available_capacity_m3", "?")
        return (
            f"I chose to route {qty} m3 of {wtype} into an existing container (id: {cid}..) "
            f"because {avail} m3 of capacity is available and the order pays {price:.2f} EUR — "
            f"profitable with no extra cost."
        )

    if action == "schedule_early_empty":
        cost = action_payload.get("early_empty_cost_eur", 0)
        margin = price - cost
        return (
            f"I chose to trigger an early empty (cost: {cost:.2f} EUR) and then route "
            f"{qty} m3 of {wtype} because the order pays {price:.2f} EUR, leaving "
            f"{margin:.2f} EUR margin after the emptying cost. "
            f"Existing capacity was too low to fit the order without clearing first."
        )

    if action == "rent_container":
        rental = action_payload.get("extra_rental_cost_eur", 0)
        cap = action_payload.get("added_capacity_m3", 0)
        return (
            f"I chose to rent a new {wtype} container ({cap:.1f} m3, cost: {rental:.2f} EUR) "
            f"because no existing container had enough capacity for {qty} m3 and "
            f"the order revenue ({price:.2f} EUR) justifies the rental investment."
        )

    if action == "reject_order":
        reason = action_payload.get("reason", "No viable path.")
        return f"I chose to reject this order: {reason}"

    return f"Chose {action} for {qty} m3 of {wtype}."

def build_result(outcome, action, eval_result, action_payload, order):
    """Build the POST /api/v1/orders/{id}/result payload."""
    request_id = eval_result.get("request_id", "")
    matched = eval_result.get("matched_rules", [])
    wtype = order["declared_waste_type"]
    qty = order["quantity_m3"]
    price = order["offered_price_eur"]

    bot_reasoning = _describe_action_reasoning(action, order, action_payload)
    guardrail_info = _format_guardrail_reasoning(eval_result)

    if outcome == "ASK_FOR_APPROVAL":
        summary = (
            f"{bot_reasoning} "
            f"However, Unreal Objects requires human approval before execution. "
            f"Triggered guardrails: {guardrail_info}"
        )
        return {
            "bot_id": BOT_ID,
            "outcome": "APPROVAL_REQUIRED",
            "bot_action": action,
            "decision_summary": summary,
            "request_id": request_id,
            "matched_rules": matched,
            "action_payload": action_payload,
        }

    if outcome == "REJECT":
        summary = (
            f"{bot_reasoning} "
            f"Unreal Objects blocked this action. "
            f"Triggered guardrails: {guardrail_info}"
        )
        return {
            "bot_id": BOT_ID,
            "outcome": "REJECTED",
            "bot_action": "reject_order",
            "decision_summary": summary,
            "request_id": request_id,
            "matched_rules": matched,
            "action_payload": {"reason": f"Guardrail rejection: {guardrail_info}"},
        }

    # APPROVE
    summary = (
        f"{bot_reasoning} "
        f"Unreal Objects approved. {guardrail_info}"
    )
    return {
        "bot_id": BOT_ID,
        "outcome": "APPROVED",
        "bot_action": action,
        "decision_summary": summary,
        "request_id": request_id,
        "matched_rules": matched,
        "action_payload": action_payload,
    }


# ── Single order pipeline (runs in a thread) ──────────────────────

def process_order(order, containers, group_id):
    """Claim → decide → evaluate → submit for one order. Returns a log line."""
    oid = order["order_id"]
    short = oid[:8]
    wtype = order["declared_waste_type"]
    qty = order["quantity_m3"]
    price = order["offered_price_eur"]

    try:
        claim_order(oid)
    except Exception as e:
        return f"{short}.. SKIP claim failed: {e}"

    action, desc, ctx, action_payload = decide_action(order, containers)

    eval_result = evaluate_action(desc, ctx, group_id)
    outcome = eval_result.get("outcome", "ASK_FOR_APPROVAL")

    result_payload = build_result(outcome, action, eval_result, action_payload, order)
    result = submit_result(oid, result_payload)

    status = result.get("status", "?")
    return f"{short}.. {wtype} {qty}m3 {action} → {outcome} ({status})"


# ── Main loop ──────────────────────────────────────────────────────

def log(tag, msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {tag}: {msg}", flush=True)

def trigger_early_empty(container_id):
    """Call the standalone early-empty endpoint on the company API."""
    return http_json(
        f"{COMPANY_BASE}/api/v1/containers/{container_id}/early-empty",
        method="POST",
        data={"bot_id": BOT_ID},
    )


def manage_containers(containers, group_id):
    """Proactively empty containers when it's cheaper than risking overflow."""
    for c in containers:
        fill_ratio = c.get("fill_ratio", 0)
        early_cost = c.get("early_empty_cost_eur", 999)
        penalty = c.get("overflow_penalty_eur", 350)
        hours_to_next_empty = c.get("hours_to_next_empty", 0)

        # Expected-value optimization: empty if cost < penalty * fill_ratio
        expected_penalty = penalty * fill_ratio

        if early_cost < expected_penalty and fill_ratio > 0.5:
            # Build guardrail context and evaluate via Decision Center
            ctx = {
                "bot_action": "schedule_early_empty",
                "overflow_prevention": True,
                "container_id": c["container_id"],
                "container_label": c["label"],
                "waste_type": c["waste_type"],
                "fill_ratio": fill_ratio,
                "early_empty_cost_eur": early_cost,
                "overflow_penalty_eur": penalty,
                "hours_to_next_empty": hours_to_next_empty,
            }
            desc = (
                f"Proactive early-empty for {c['label']} "
                f"(fill: {fill_ratio:.0%}, cost: €{early_cost:.0f}, "
                f"next pickup in {hours_to_next_empty:.0f}h)"
            )
            try:
                eval_result = evaluate_action(desc, ctx, group_id)
                outcome = eval_result.get("outcome", "ASK_FOR_APPROVAL")

                if outcome in ("APPROVE", "APPROVED"):
                    trigger_early_empty(c["container_id"])
                    log("EMPTY", f"{c['label']} emptied (fill: {fill_ratio:.0%}, cost: €{early_cost:.0f} vs penalty: €{penalty:.0f})")
                elif outcome in ("REJECT", "REJECTED"):
                    reasoning = _format_guardrail_reasoning(eval_result)
                    log("SKIP", f"{c['label']} early-empty rejected by guardrails: {reasoning}")
                else:
                    log("HOLD", f"{c['label']} early-empty needs approval (fill: {fill_ratio:.0%})")
            except Exception as e:
                log("ERR", f"Early empty {c['label']}: {e}")


def wait_for_services():
    """Block until the company API and decision center are reachable."""
    log("WAIT", "Waiting for company API and decision center...")
    for label, url in [("Company API", f"{COMPANY_BASE}/api/v1/status"),
                        ("Decision Center", f"{DECISION_CENTER}/v1/health")]:
        for attempt in range(120):
            try:
                http_json(url, timeout=5)
                log("WAIT", f"{label} ready")
                break
            except Exception:
                if attempt % 10 == 0:
                    log("WAIT", f"{label} not ready yet (attempt {attempt})...")
                time.sleep(2)

def run():
    wait_for_services()

    # Discover group_id from the company server
    group_id = None
    for _ in range(30):
        group_id = fetch_group_id()
        if group_id:
            break
        time.sleep(2)

    if not group_id:
        log("FATAL", "Could not discover rule group_id from company API")
        return

    log("BOOT", f"Worker started — group={group_id} concurrency={CONCURRENCY} batch={BATCH_SIZE} poll={POLL_INTERVAL}s")

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        while True:
            try:
                containers = fetch_containers()

                # Proactive container management — run before orders
                manage_containers(containers, group_id)

                orders = fetch_open_orders()
                if not orders:
                    time.sleep(POLL_INTERVAL)
                    continue

                # Rank and take a batch
                batch = rank_orders(orders)[:BATCH_SIZE]
                # Re-fetch containers after proactive empties
                containers = fetch_containers()

                log("BATCH", f"{len(batch)} orders (of {len(orders)} open)")

                # Submit all orders in the batch concurrently
                futures = {
                    pool.submit(process_order, order, containers, group_id): order
                    for order in batch
                }

                for future in as_completed(futures):
                    try:
                        msg = future.result()
                        log("DONE", msg)
                    except Exception as e:
                        order = futures[future]
                        log("ERR", f"{order['order_id'][:8]}.. {repr(e)}")

            except Exception as e:
                log("ERR", repr(e))

            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
