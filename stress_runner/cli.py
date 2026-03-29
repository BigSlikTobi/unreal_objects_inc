"""CLI entrypoint for waste-company batch runs."""

import asyncio
import click
from pathlib import Path

from .runner import run_stress_test
from .report import save_report, print_summary
from support_company.simulator import DEFAULT_LLM_MODEL

DEFAULT_RULE_PACK = Path(__file__).resolve().parent.parent / "rule_packs" / "support_company.json"


@click.command()
@click.option("--cases", default=50, help="Number of disposal orders to generate.")
@click.option("--seed", default=42, help="Random seed for reproducibility.")
@click.option("--concurrency", default=5, help="Max parallel disposal-order evaluations.")
@click.option(
    "--generator-mode",
    type=click.Choice(["mixed", "llm", "template"], case_sensitive=False),
    default="mixed",
    help="Use mixed LLM+template scenarios, LLM-first generation, or deterministic templates.",
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
    help="Path to rule pack JSON.",
)
@click.option("--rule-engine-url", default="http://127.0.0.1:8001")
@click.option("--decision-center-url", default="http://127.0.0.1:8002")
def main(
    cases: int,
    seed: int,
    concurrency: int,
    generator_mode: str,
    llm_model: str,
    allow_template_fallback: bool,
    rule_pack: str,
    rule_engine_url: str,
    decision_center_url: str,
):
    """Run a batch simulation of the waste bot against Unreal Objects."""
    result = asyncio.run(
        run_stress_test(
            rule_pack_path=rule_pack,
            case_count=cases,
            seed=seed,
            concurrency=concurrency,
            rule_engine_url=rule_engine_url,
            decision_center_url=decision_center_url,
            generator_mode=generator_mode,
            llm_model=llm_model,
            allow_template_fallback=allow_template_fallback,
        )
    )

    print_summary(result)
    path = save_report(result)
    click.echo(f"\nReport saved to {path}")


if __name__ == "__main__":
    main()
