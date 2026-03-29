# unreal_objects_inc

`unreal_objects_inc` is a simulated waste-management company that uses an autonomous bot under Unreal Objects guardrails.

This repo is not the governance system itself. The governance system lives in `unreal_objects/`. This repo is the company around it: disposal orders come in, containers fill up, pickup and exchange costs accrue as servicing happens, emptying cycles run, and an external bot tries to keep the business profitable while staying inside the Unreal Objects rules.

## Simple Story

1. A company creates waste-operation guardrails in `unreal_objects`
2. A company creates an MCP from those guardrails
3. A company gives that MCP to an autonomous waste bot
4. This repo simulates disposal orders, container fleets, pickup and exchange costs, and emptying cycles
5. The bot chooses actions autonomously to maximize profit
6. The bot checks each chosen action against Unreal Objects
7. The bot sends the guarded result back to the company
8. The company tracks cashflow, overflow events, and bankruptcies across runs

Points 1 to 3 happen outside this repo. This repo covers points 4 to 8.

## What Runs Here

- `company_api/`: the company server on port `8010`
- `support_company/`: disposal-order and container simulation
- `bot_adapter/`: the bot’s adapter into Unreal Objects
- `stress_runner/`: batch simulation and reporting
- `dashboard/`: the company operations dashboard
- `rule_packs/`: waste-management guardrails loaded into Unreal Objects
- `scripts/`: local helper scripts such as stack startup and rule-pack loading
- `unreal_objects/`: the external guardrail system as a git submodule

## Runtime Model

The company tracks:

- disposal orders with waste type, quantity, price, and service window
- containers with waste type, capacity, standard exchange cost, and emptying cadence
- overflow events when capacity is exceeded
- receivables, payables, recurring burn, cash balance, and realized profit
- bankruptcy count across restarts

The company is now modeled as a cashflow business, not an instant-margin counter:

- completed work creates an invoice first, not immediate cash
- cash only lands after a payment delay
- overhead accrues continuously over virtual time
- pickup and exchange costs are only triggered when containers are actually serviced
- service execution creates company-side operating cost and liabilities
- bankruptcy is driven by liquidity, not by a single instant profit figure

The default startup snapshot is intentionally survivable but not generous:

- the yard starts lightly loaded instead of near saturation
- the company has enough working capital to survive normal invoice/payment delay
- the default order mix is weighted toward billable work, with approval-heavy jobs still present but not dominant
- the economics are tuned for modest positive margins, not “easy money”

When cash falls below the bankruptcy threshold, the company restarts with a fresh fleet and empty order book, but keeps the bankruptcy counter.

## Bot Model

The bot is external to this repo.

The company exposes raw work. The bot decides what to do. Typical actions are:

- `accept_and_route`
- `reject_order`
- `rent_container`
- `schedule_early_empty`

The important sequence is:

1. The bot reads a raw disposal order
2. The bot decides on an action autonomously
3. The bot checks that chosen action with Unreal Objects
4. The bot sends the guarded result back to the company

This repo does not tell the bot which action to take.

## Economics Model

The simulation is intentionally harsher and more realistic than before.

- customer quotes are not treated as instant profit
- accepted orders become receivables first
- service work creates operating cost based on waste type, urgency, and risk
- owned-fleet containers do not create recurring rental burn
- standard emptying creates pickup and exchange cost only when servicing actually happens
- depot overhead burns cash continuously
- extra rentals and early emptying create near-term liabilities

This means a fast bot can no longer produce implausible profit in a few virtual minutes just by completing a burst of orders. The important operating questions are now:

- is the bot generating sustainable cashflow?
- is it building too much receivable exposure?
- is it taking actions that stress liquidity?
- do the Unreal Objects guardrails keep that autonomy commercially safe?

## Local Run

For the full repeatable startup flow, including LAN bot setup and MCP enrollment, use [SETUP.md](/Users/tobiaslatta/Projects/github/bigsliktobi/unreal_objects_inc/SETUP.md).

Python 3.11+ and Node.js 18+ are required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
git submodule update --init
```

Start Unreal Objects:

```bash
bash scripts/start_full_stack.sh
```

The Rule Engine now persists its live rule groups under
`unreal_objects/data/rule_engine_store.json`. That file is runtime-only and
gitignored, so the active company rules survive restarts without being committed
to source control.

Load the waste rule pack into the Unreal Objects Rule Engine:

```bash
python3 scripts/load_rule_pack.py
```

Start the company server in continuous mode at 24x speed:

```bash
uo-company-server --host 0.0.0.0 --port 8010
```

Or seed a fixed batch of disposal orders:

```bash
uo-company-server --host 0.0.0.0 --port 8010 --cases 24 --seed 42
```

Or roll in a bounded total gradually over time:

```bash
uo-company-server --host 0.0.0.0 --port 8010 --cases 1000 --rolling --seed 42
```

Rolling generation is now tied to simulated time instead of a fixed real-time burst. By default, the company targets roughly `1000` orders per simulated day, which works out to a new order roughly every `2.7s` to `4.5s` in real time at the default clock speed.

By default, the company server will auto-discover live rule groups from Unreal Objects and mirror them in the dashboard when the Rule Engine is reachable.

If you want to pin the dashboard to one specific live group, start the company server with:

```bash
uo-company-server --host 0.0.0.0 --port 8010 --rule-group-id <GROUP_ID>
```

For mixed generation, put `OPENAI_API_KEY=...` in a local `.env` file or export it in your shell. The company server and batch runner default to `--generator-mode mixed` with `gpt-5.4-mini-2026-03-17`: part of the stream comes from the LLM and part comes from deterministic templates. If the LLM is unavailable, the missing share falls back to deterministic templates unless you disable fallback.

At the default `24x` acceleration, `1` real hour equals `1` simulated day.

Start the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5174`.

## Company APIs

Bot-facing raw work:

- `GET /api/v1/orders`
- `POST /api/v1/orders/{order_id}/claim`
- `POST /api/v1/orders/{order_id}/result`

Dashboard/company views:

- `GET /api/v1/status`
- `GET /api/v1/clock`
- `GET /api/v1/dashboard/orders`
- `GET /api/v1/containers`
- `GET /api/v1/economics`
- `GET /api/v1/pricing`
- `GET /api/v1/rules`
- `GET /api/v1/events`

The economics endpoint now exposes liquidity and burn, including:

- `cash_balance_eur`
- `accounts_receivable_eur`
- `accounts_payable_eur`
- `invoiced_revenue_eur`
- `operating_cost_eur`
- `daily_burn_eur`

## Batch Simulation

You can also run a batch simulation without the dashboard:

```bash
uo-stress-company --cases 50 --seed 42
```

Reports are written to `reports/`.

## Testing

```bash
pytest -v
pytest tests/test_generator.py tests/test_simulator.py tests/test_company_service.py -v
```

## Glossary

- Guardrails: rules from Unreal Objects that constrain the bot’s chosen action
- Overflow: a container exceeded safe capacity before timely emptying
- Bankruptcy: the company ran out of safe liquidity and restarted
- Continuous mode: endless order generation when `--cases` is omitted
