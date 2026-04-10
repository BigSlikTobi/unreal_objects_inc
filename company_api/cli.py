"""CLI for running the simulated waste-company API server."""

from pathlib import Path

import click
import uvicorn

from .app import build_app
from support_company.simulator import DEFAULT_LLM_MODEL
from .service import DEFAULT_ACCELERATION


DEFAULT_RULE_PACK = Path(__file__).resolve().parent.parent / "rule_packs" / "support_company.json"


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the company API server.")
@click.option("--port", default=8010, help="Port to bind the company API server.")
@click.option("--cases", default=None, type=int, help="Number of initial disposal orders to seed. Omit for continuous mode.")
@click.option("--rolling/--no-rolling", default=False, help="Generate bounded orders gradually over time instead of seeding them all at once.")
@click.option("--seed", default=42, help="Seed for deterministic case generation.")
@click.option("--acceleration", default=DEFAULT_ACCELERATION, help="Virtual clock acceleration multiplier.")
@click.option("--order-interval", default=60.0, type=float, help="Average real-time seconds between new orders.")
@click.option("--deployment-mode", type=click.Choice(["local", "hosted"], case_sensitive=False), default="local", help="Run in local LAN mode or hosted public mode.")
@click.option("--rule-engine-url", default="http://127.0.0.1:8001", help="Unreal Objects Rule Engine base URL.")
@click.option("--decision-center-url", default="http://127.0.0.1:8002", help="Unreal Objects Decision Center base URL.")
@click.option("--rule-group-id", default=None, help="Live Unreal Objects rule group to mirror in the dashboard.")
@click.option("--public-voting/--no-public-voting", default=None, help="Enable public voting on approval items.")
@click.option("--operator-auth/--no-operator-auth", default=None, help="Require an operator token for approval finalization.")
@click.option("--operator-token", default=None, help="Shared operator token used for protected approval finalization.")
@click.option("--internal-api-key", default=None, help="Shared internal API key sent as X-Internal-Key to Unreal Objects services.")
@click.option("--persistence-path", default=None, type=click.Path(), help="Optional JSON snapshot path for persisted hosted state.")
@click.option("--cost-policy", default=None, type=click.Path(exists=True), help="Optional JSON file with cost policy overrides.")
@click.option(
    "--generator-mode",
    type=click.Choice(["mixed", "llm", "template"], case_sensitive=False),
    default="mixed",
    help="Use a mixed LLM+template stream, pure LLM-first generation, or deterministic templates.",
)
@click.option("--llm-model", default=DEFAULT_LLM_MODEL, help="OpenAI model used for scenario generation.")
@click.option(
    "--allow-template-fallback/--no-allow-template-fallback",
    default=True,
    help="Fall back to deterministic templates if the LLM is unavailable.",
)
@click.option(
    "--rule-pack",
    type=click.Path(exists=True),
    default=str(DEFAULT_RULE_PACK),
    help="Path to the rule pack JSON file to load into Unreal Objects.",
)
def main(
    host: str,
    port: int,
    cases: int | None,
    rolling: bool,
    seed: int,
    acceleration: int,
    order_interval: float,
    deployment_mode: str,
    rule_engine_url: str,
    decision_center_url: str,
    rule_group_id: str | None,
    public_voting: bool | None,
    operator_auth: bool | None,
    operator_token: str | None,
    internal_api_key: str | None,
    persistence_path: str | None,
    cost_policy: str | None,
    generator_mode: str,
    llm_model: str,
    allow_template_fallback: bool,
    rule_pack: str,
) -> None:
    """Run the Unreal Objects Inc waste-company server."""
    if rolling and cases is None:
        raise click.BadOptionUsage("--rolling", "--rolling requires --cases so the server knows the total bounded order count.")

    app = build_app(
        rule_pack_path=rule_pack,
        initial_order_count=cases,
        rolling_generation=rolling,
        seed=seed,
        acceleration=acceleration,
        order_interval=order_interval,
        deployment_mode=deployment_mode,
        generator_mode=generator_mode,
        rule_engine_url=rule_engine_url,
        decision_center_url=decision_center_url,
        rule_group_id=rule_group_id,
        public_voting_enabled=public_voting,
        operator_auth_enabled=operator_auth,
        operator_token=operator_token,
        internal_api_key=internal_api_key,
        persistence_path=persistence_path,
        cost_policy_path=cost_policy,
        llm_model=llm_model,
        allow_template_fallback=allow_template_fallback,
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
