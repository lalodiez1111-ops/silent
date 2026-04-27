"""CLI entrypoint for the solo operator agent system."""

from __future__ import annotations

import argparse
from pathlib import Path

from .orchestrator import AgentOrchestrator
from .ui_server import serve_ui
from .utils import default_output_dir, path_from_root


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Run a lean solo-operator agent for lead sourcing, company research, or content repurposing."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one agent with a JSON input file.")
    run_parser.add_argument("agent", choices=["lead", "research", "content"], help="Agent to run.")
    run_parser.add_argument("--input", help="Path to the input JSON file.")
    run_parser.add_argument("--csv", help="Path to a CSV file for lead import.")
    run_parser.add_argument("--limit", type=int, help="Limit the number of imported CSV rows.")
    run_parser.add_argument("--output-name", help="Optional label to include in output filenames.")
    run_parser.add_argument(
        "--use-sample",
        action="store_true",
        help="Use the built-in sample input for the selected agent.",
    )
    run_parser.add_argument(
        "--preferences",
        default=str(path_from_root("config", "preferences.example.json")),
        help="Path to preferences JSON.",
    )
    run_parser.add_argument(
        "--sources",
        default=str(path_from_root("config", "sources.example.json")),
        help="Path to sources JSON.",
    )
    run_parser.add_argument(
        "--output-dir",
        default=str(default_output_dir()),
        help="Directory where JSON and Markdown outputs are saved.",
    )

    sample_parser = subparsers.add_parser("sample", help="Show the built-in sample input path for an agent.")
    sample_parser.add_argument("agent", choices=["lead", "research", "content"], help="Agent to inspect.")

    ui_parser = subparsers.add_parser("ui", help="Run the local Silent Agents button-based UI.")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Host to bind the UI server.")
    ui_parser.add_argument("--port", type=int, default=8123, help="Port to bind the UI server.")
    return parser


def default_sample_input_path(agent: str) -> Path:
    """Return the bundled sample input path for a given agent."""
    sample_paths = {
        "lead": path_from_root("agents", "lead_sourcing", "sample_input.json"),
        "research": path_from_root("agents", "company_research", "sample_input.json"),
        "content": path_from_root("agents", "content_repurposing", "sample_input.json"),
    }
    return sample_paths[agent]


def main() -> None:
    """Parse CLI arguments, run the selected agent, and print a concise summary."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "sample":
        print(default_sample_input_path(args.agent))
        return

    if args.command == "ui":
        serve_ui(host=args.host, port=args.port)
        return

    input_path = args.input
    csv_path = args.csv
    if args.use_sample:
        input_path = str(default_sample_input_path(args.agent))

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")

    if args.agent != "lead" and csv_path:
        parser.error("--csv is currently supported only for the lead agent")

    if csv_path and args.use_sample:
        parser.error("use either --csv or --use-sample, not both")

    if csv_path and args.input:
        parser.error("use either --csv or --input, not both")

    if not input_path and not csv_path:
        parser.error("the following arguments are required: --input, --csv, or --use-sample")

    orchestrator = AgentOrchestrator(
        preferences_path=args.preferences,
        sources_path=args.sources,
        output_dir=args.output_dir,
    )
    try:
        data, _markdown, artifacts = orchestrator.run(
            agent=args.agent,
            input_path=input_path,
            csv_path=csv_path,
            limit=args.limit,
            output_name=args.output_name,
        )
    except FileNotFoundError as exc:
        parser.exit(2, f"Error: {exc}\n")
    except ValueError as exc:
        parser.exit(2, f"Error: {exc}\n")

    print(f"Agent run complete: {args.agent}")
    print(f"JSON saved to: {Path(artifacts.json_path)}")
    print(f"Markdown saved to: {Path(artifacts.markdown_path)}")

    if args.agent == "lead":
        print(f"Leads returned: {len(data)}")
        if data:
            top = data[0]
            print(f"Top lead: {top['company_name']} ({top['priority_score']}/5)")
    elif args.agent == "research":
        print(f"Company: {data['company_name']}")
        print(f"Recommended angle: {data['recommended_service_angle']}")
    elif args.agent == "content":
        print(f"Lane: {data['target_lane']}")
        print(f"Headline option: {data['headline_options'][0]}")


if __name__ == "__main__":
    main()
