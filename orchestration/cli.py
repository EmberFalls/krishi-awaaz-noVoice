from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy.exc import SQLAlchemyError

from agents.models import DialogueLine, SimulationResult, SimulationScenario, SpeakerType
from agents.negotiation import display_number
from data.scenarios import find_scenario, load_scenarios
from db.database import PostgresStore
from telephony.service import run_scripted_voice_call

from .config import Settings
from .workflow import execute_scenario

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


SPEAKER_LABELS = {
    SpeakerType.FARMER: "Farmer",
    SpeakerType.INTAKE_AGENT: "Intake agent",
    SpeakerType.NEGOTIATION_AGENT: "Negotiation agent",
    SpeakerType.MIDDLEMAN: "Middleman",
    SpeakerType.REPORTING_AGENT: "Reporting agent",
    SpeakerType.SYSTEM: "System",
}


def render_dialogue(lines: list[DialogueLine]) -> None:
    for index, line in enumerate(lines, 1):
        label = SPEAKER_LABELS[line.speaker]
        console.print(f"[bold cyan]{index:02d} {label}[/bold cyan] [{line.language}]")
        console.print(f"   {line.text}")
        if line.english_translation != line.text:
            console.print(f"   [dim]English: {line.english_translation}[/dim]")


def render_scenario_summary(scenario: SimulationScenario, reveal_hidden: bool = False) -> None:
    listing = scenario.listing
    farmer = scenario.farmer
    details = Table(show_header=False, box=None)
    details.add_row("Scenario", scenario.id)
    details.add_row("Farmer", farmer.name)
    details.add_row("Location", farmer.location.label)
    details.add_row("Language", f"{farmer.preferred_language_name} ({farmer.preferred_language})")
    details.add_row("Produce", f"{listing.quantity_quintal} quintals of {listing.variety}")
    details.add_row("Quality", listing.quality_grade)
    details.add_row("Floor", f"₹{display_number(listing.minimum_price_per_quintal)}/quintal")
    details.add_row("Urgency", f"{listing.urgency_hours} hours")
    console.print(Panel(details, title=scenario.title))

    buyers = Table(title="Simulated middlemen")
    buyers.add_column("Business")
    buyers.add_column("Market")
    buyers.add_column("Language")
    buyers.add_column("Opening")
    if reveal_hidden:
        buyers.add_column("Hidden ceiling", style="yellow")
    buyers.add_column("Pickup")
    buyers.add_column("Payment")
    buyers.add_column("Reliability")
    for middleman in scenario.middlemen:
        row = [
            middleman.business_name,
            middleman.market_id,
            middleman.preferred_language,
            f"₹{display_number(middleman.initial_offer_per_quintal)}",
        ]
        if reveal_hidden:
            row.append(f"₹{display_number(middleman.maximum_offer_per_quintal)}")
        row.extend(
            [
                "yes" if middleman.pickup_available else "no",
                f"{middleman.payment_delay_days} day(s)",
                f"{middleman.reliability_score}/5",
            ]
        )
        buyers.add_row(*row)
    console.print(buyers)


def render_result(result: SimulationResult) -> None:
    console.rule("[bold]Farmer intake conversation")
    render_dialogue(result.intake_dialogue)

    markets = Table(title="Decision agent: synthetic market comparison")
    markets.add_column("Rank", justify="right")
    markets.add_column("Market")
    markets.add_column("Modal price", justify="right")
    markets.add_column("Distance", justify="right")
    markets.add_column("Net / quintal", justify="right")
    markets.add_column("Data age", justify="right")
    for assessment in result.market_assessments:
        market = assessment.market
        markets.add_row(
            str(assessment.rank),
            market.market_name,
            f"₹{display_number(market.modal_price_per_quintal)}",
            f"{market.distance_km} km",
            f"₹{display_number(assessment.estimated_net_per_quintal)}",
            f"{market.data_age_hours}h",
        )
    console.print(markets)

    for offer in result.offers:
        console.rule(f"[bold]Negotiation: {offer.business_name}")
        render_dialogue(offer.conversation)

    offers = Table(title="Provisional offer ranking")
    offers.add_column("Rank", justify="right")
    offers.add_column("Middleman")
    offers.add_column("Opening", justify="right")
    offers.add_column("Final", justify="right")
    offers.add_column("Pickup")
    offers.add_column("Payment")
    offers.add_column("Est. net", justify="right")
    offers.add_column("Risk-adjusted", justify="right")
    offers.add_column("Status")
    for offer in result.offers:
        offers.add_row(
            str(offer.rank or "—"),
            offer.business_name,
            f"₹{display_number(offer.initial_price_per_quintal)}",
            f"₹{display_number(offer.final_price_per_quintal)}",
            "yes" if offer.pickup_available else "no",
            f"{offer.payment_delay_days} day(s)",
            f"₹{display_number(offer.estimated_net_total)}",
            f"₹{display_number(offer.risk_adjusted_total)}",
            offer.status.value,
        )
    console.print(offers)

    console.print(Panel(result.report_text, title="Reporting agent", border_style="green"))
    timeline = Table(title="Workflow trace")
    timeline.add_column("Node")
    timeline.add_column("Result")
    for event in result.events:
        timeline.add_row(event.node, event.message)
    console.print(timeline)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Krishi Awaaz text workflow simulator")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("data/scenarios.json"),
        help="Path to the multilingual scenario catalog",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List available farmer scenarios")

    show = commands.add_parser("show", help="Show one scenario and hidden simulator settings")
    show.add_argument("scenario_id")

    run = commands.add_parser("run", help="Execute one scenario")
    run.add_argument("scenario_id")
    run.add_argument(
        "--no-db",
        action="store_true",
        help="Run without PostgreSQL persistence (useful for reviewing the simulator)",
    )
    run.add_argument("--json", action="store_true", help="Print machine-readable result JSON")

    voice_demo = commands.add_parser(
        "voice-demo",
        help="Replay scripted intake through local simulated speech adapters",
    )
    voice_demo.add_argument("scenario_id")
    voice_demo.add_argument("--json", action="store_true", help="Print machine-readable call data")

    commands.add_parser("db-init", help="Create PostgreSQL tables and seed all participants")
    calls = commands.add_parser("calls", help="List recent persisted voice-call sessions")
    calls.add_argument(
        "--limit", type=int, default=20, help="Maximum calls to display (default: 20)"
    )
    return parser


def list_scenarios(scenarios: list[SimulationScenario]) -> None:
    table = Table(title="Krishi Awaaz scenarios")
    table.add_column("ID")
    table.add_column("Farmer")
    table.add_column("Language")
    table.add_column("Location")
    table.add_column("Listing")
    table.add_column("Middlemen", justify="right")
    for scenario in scenarios:
        table.add_row(
            scenario.id,
            scenario.farmer.name,
            scenario.farmer.preferred_language_name,
            scenario.farmer.location.label,
            f"{scenario.listing.quantity_quintal} q {scenario.listing.crop}",
            str(len(scenario.middlemen)),
        )
    console.print(table)


def persist_result(
    settings: Settings,
    scenarios: list[SimulationScenario],
    scenario: SimulationScenario,
    result: SimulationResult,
) -> None:
    store = PostgresStore(settings.database_url)
    try:
        store.create_schema()
        store.seed_scenarios(scenarios)
        store.save_result(scenario, result)
    finally:
        store.close()


def render_call_history(settings: Settings, limit: int) -> int:
    if limit < 1:
        console.print("[bold red]--limit must be at least 1.[/bold red]")
        return 2
    store = PostgresStore(settings.database_url)
    try:
        calls = store.list_voice_calls(limit)
    except SQLAlchemyError as exc:
        console.print(f"[bold red]Could not read PostgreSQL call history:[/bold red] {exc}")
        return 1
    finally:
        store.close()
    if not calls:
        console.print("[yellow]No persisted voice calls yet.[/yellow]")
        return 0
    table = Table(title="Recent voice calls")
    table.add_column("Call ID")
    table.add_column("Scenario")
    table.add_column("Language")
    table.add_column("Status")
    table.add_column("Updated")
    table.add_column("Workflow run")
    for call in calls:
        table.add_row(
            str(call["call_id"]),
            str(call["scenario_id"]),
            str(call["language"]),
            str(call["status"]),
            str(call["updated_at"]),
            str(call["simulation_run_id"] or "—"),
        )
    console.print(table)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_environment(args.scenarios)
    scenarios = load_scenarios(settings.scenario_file)

    if args.command == "list":
        list_scenarios(scenarios)
        return 0

    if args.command == "show":
        render_scenario_summary(find_scenario(scenarios, args.scenario_id), reveal_hidden=True)
        return 0

    if args.command == "db-init":
        store = PostgresStore(settings.database_url)
        try:
            store.create_schema()
            store.seed_scenarios(scenarios)
        except SQLAlchemyError as exc:
            console.print(f"[bold red]PostgreSQL initialization failed:[/bold red] {exc}")
            return 1
        finally:
            store.close()
        console.print(f"[green]Seeded {len(scenarios)} scenarios into PostgreSQL.[/green]")
        return 0

    if args.command == "calls":
        return render_call_history(settings, args.limit)

    if args.command == "voice-demo":
        scenario = find_scenario(scenarios, args.scenario_id)
        voice_call = asyncio.run(run_scripted_voice_call(scenario))
        if args.json:
            console.print_json(json.dumps(voice_call.model_dump(mode="json"), ensure_ascii=False))
        else:
            console.print(
                Panel(
                    "Local simulated call completed. No phone provider, audio API, or database was used.",
                    title=f"Voice demo: {voice_call.session.call_id}",
                    border_style="cyan",
                )
            )
            render_result(voice_call.workflow_result)
        return 0

    scenario = find_scenario(scenarios, args.scenario_id)
    result = asyncio.run(execute_scenario(scenario))
    if args.json:
        console.print_json(json.dumps(result.model_dump(mode="json"), ensure_ascii=False))
    else:
        render_scenario_summary(scenario)
        render_result(result)

    if not args.no_db:
        try:
            persist_result(settings, scenarios, scenario, result)
        except SQLAlchemyError as exc:
            console.print(
                "[bold red]Simulation completed, but PostgreSQL persistence failed.[/bold red]\n"
                f"{exc}\nRun with --no-db to review without a database."
            )
            return 1
        console.print(f"[green]Saved run {result.run_id} to PostgreSQL.[/green]")
    else:
        console.print("[yellow]Review mode: result was not persisted (--no-db).[/yellow]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
