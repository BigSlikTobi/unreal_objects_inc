"""Report writer for waste-company batch runs."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .models import StressRunResult


REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def save_report(result: StressRunResult) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    filename = f"run_{result.run_id[:8]}_{result.started_at:%Y%m%d_%H%M%S}.json"
    path = REPORTS_DIR / filename
    path.write_text(result.model_dump_json(indent=2))
    return path


def print_summary(result: StressRunResult) -> None:
    console = Console()
    console.print(f"\n[bold]Waste Company Run {result.run_id[:8]}[/bold]")
    console.print(f"Seed: {result.seed}  |  Orders: {result.total_orders}")
    if result.finished_at and result.started_at:
        elapsed = (result.finished_at - result.started_at).total_seconds()
        console.print(f"Duration: {elapsed:.1f}s")

    table = Table(title="Outcome Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("APPROVED", str(result.approve_count))
    table.add_row("APPROVAL_REQUIRED", str(result.ask_for_approval_count))
    table.add_row("REJECTED", str(result.reject_count))
    table.add_row("ERROR", str(result.error_count))
    table.add_row("Path accuracy", f"{result.path_accuracy:.1f}%")
    console.print(table)
