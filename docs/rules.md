# Waste Company Rules

This file is the recommended manual ruleset for `unreal_objects_inc` in its waste-management setup.

The goal is not to tell the bot what to do. The bot should choose an action autonomously. These rules only constrain the chosen action.

## Principle

Use rules that check the bot's chosen action, not the raw disposal order.

Good:

- "If the bot wants to route hazardous waste into non-hazardous capacity, reject."
- "If the bot wants to rent very expensive extra capacity, ask for approval."

Bad:

- "If the order is urgent residual waste, ask for approval."

The second one is too early in the decision chain. The bot must first decide what it wants to do.

## Datapoints To Use

These are the datapoints the current bot/runtime can already send into Unreal Objects:

- `declared_waste_type`
- `quantity_m3`
- `offered_price_eur`
- `priority`
- `service_window`
- `hazardous_flag`
- `contamination_risk`
- `bot_action`
- `target_waste_type`
- `target_container_type`
- `available_capacity_m3`
- `route_quantity_m3`
- `added_capacity_m3`
- `extra_rental_cost_eur`
- `early_empty_cost_eur`

Current bot action values:

- `accept_and_route`
- `reject_order`
- `rent_container`
- `schedule_early_empty`

## Rule Design Guidance

- Keep rules narrow and action-specific.
- Prefer `else: null` for non-matching cases.
- Avoid broad `ELSE APPROVE` branches.
- Let the most restrictive matching rule win.
- Use approval only where a human really adds value.
- Reject only for safety, legal, or clearly loss-making actions.

## Recommended Minimum Rules

These are the rules I would create first.

### 1. Hazardous Waste Must Stay In Hazardous Handling

Importance:
- Critical

Why:
- This is the most basic safety guardrail.

Suggested logic:
- If `declared_waste_type == hazardous`
- And `bot_action == accept_and_route`
- And `target_waste_type != hazardous`
- Then `REJECT`

### 2. Large Hazardous Loads Must Not Be Auto-Handled

Importance:
- Critical

Why:
- Small hazardous work can be approval-gated.
- Large hazardous work should not be routed automatically.

Suggested logic:
- If `declared_waste_type == hazardous`
- And `quantity_m3 >= 6`
- And `bot_action != reject_order`
- Then `REJECT`

### 3. Smaller Hazardous Loads Require Approval

Importance:
- Critical

Why:
- Hazardous work should not pass fully automatically just because it is small.

Suggested logic:
- If `declared_waste_type == hazardous`
- And `quantity_m3 < 6`
- And `bot_action != reject_order`
- Then `ASK_FOR_APPROVAL`

### 4. Overflow-Causing Routes Are Rejected

Importance:
- Critical

Why:
- The company should never knowingly overfill a container.

Suggested logic:
- If `bot_action == accept_and_route`
- And `route_quantity_m3 > available_capacity_m3`
- Then `REJECT`

### 5. Large Extra Rentals Require Approval

Importance:
- High

Why:
- Extra capacity can be a good decision, but large rentals should be visible.

Suggested logic:
- If `bot_action == rent_container`
- And `added_capacity_m3 > 12`
- Then `ASK_FOR_APPROVAL`

Alternative version:
- Also ask for approval if `extra_rental_cost_eur > 500`

### 6. Expensive Early Emptying Requires Approval

Importance:
- High

Why:
- Early emptying is often operationally useful, but expensive emergency actions should be visible.

Suggested logic:
- If `bot_action == schedule_early_empty`
- And `early_empty_cost_eur > 150`
- Then `ASK_FOR_APPROVAL`

### 7. Loss-Making Actions Are Rejected

Importance:
- High

Why:
- The company objective is profitability.
- If a chosen action already guarantees a loss, the guardrails should stop it.

Suggested logic:
- If `extra_rental_cost_eur + early_empty_cost_eur > offered_price_eur`
- Then `REJECT`

This is intentionally simple.
It does not model every business cost, but it catches obviously bad actions.

### 8. Contamination-Risk Loads Must Not Be Routed Across Waste Types

Importance:
- High

Why:
- Contamination-risk loads should not be handled loosely.

Suggested logic:
- If `contamination_risk == true`
- And `bot_action == accept_and_route`
- And `target_waste_type != declared_waste_type`
- Then `REJECT`

### 9. Urgent Same-Day Emergency Actions Should Be Visible

Importance:
- Medium

Why:
- Same-day work is not automatically bad, but combining urgency with an emergency action is the kind of thing many operators want surfaced.

Suggested logic:
- If `priority == urgent`
- And `service_window == same_day`
- And `bot_action == schedule_early_empty`
- Then `ASK_FOR_APPROVAL`

Use this only if you want tighter operational control.

### 10. Large Rental On Low-Revenue Orders Is Not Allowed

Importance:
- Medium

Why:
- This catches cases where the bot tries to buy too much flexibility for too little revenue.

Suggested logic:
- If `bot_action == rent_container`
- And `extra_rental_cost_eur > offered_price_eur`
- Then `REJECT`

This overlaps a bit with the loss-making rule, but it is easier to explain in the UI and logs.

## Recommended Creation Order In Unreal Objects

If you want the fastest useful setup, create them in this order:

1. Hazardous Waste Must Stay In Hazardous Handling
2. Large Hazardous Loads Must Not Be Auto-Handled
3. Smaller Hazardous Loads Require Approval
4. Overflow-Causing Routes Are Rejected
5. Loss-Making Actions Are Rejected
6. Large Extra Rentals Require Approval
7. Expensive Early Emptying Requires Approval
8. Contamination-Risk Loads Must Not Be Routed Across Waste Types

That is enough for a strong first run.

## Rules I Would Not Add Yet

I would avoid these for now:

- Very detailed price-threshold rules for every waste type
- Many approval thresholds that overlap heavily
- Rules that try to predict the correct action from the order alone
- Rules that depend on datapoints the bot does not currently send

Too many overlapping rules will make the bot behavior harder to understand.

## If You Want One Lean Starter Set

Use only these six rules first:

1. Hazardous Waste Must Stay In Hazardous Handling
2. Large Hazardous Loads Must Not Be Auto-Handled
3. Smaller Hazardous Loads Require Approval
4. Overflow-Causing Routes Are Rejected
5. Large Extra Rentals Require Approval
6. Loss-Making Actions Are Rejected

That set gives you:

- hard safety limits
- hard capacity limits
- one approval path
- one economic sanity check

It is usually enough to get a meaningful autonomous run without over-constraining the bot.
