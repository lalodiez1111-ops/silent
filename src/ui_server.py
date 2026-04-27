"""Tiny local web server for the Silent Agents UI."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .orchestrator import AgentOrchestrator
from .utils import default_output_dir, path_from_root


class SilentAgentsHandler(BaseHTTPRequestHandler):
    """Serve the UI and expose minimal local agent-run endpoints."""

    server_version = "SilentAgents/0.1"

    @property
    def orchestrator(self) -> AgentOrchestrator:
        return self.server.orchestrator  # type: ignore[attr-defined]

    def log_message(self, format: str, *args) -> None:
        """Keep request logging concise."""
        super().log_message(format, *args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/agents-ui", "/agents-ui.html"}:
            ui_path = path_from_root("agents-ui.html")
            if not ui_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "agents-ui.html not found")
                return
            body = ui_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            self._handle_run()
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_run(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        agent = payload.get("agent")
        if agent not in {"lead", "research", "content"}:
            self._send_json({"error": "Unsupported agent."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            if agent == "lead":
                limit = payload.get("limit")
                if limit is not None:
                    try:
                        limit = int(limit)
                    except (TypeError, ValueError):
                        raise ValueError("Lead limit must be a positive integer.")
                    if limit <= 0:
                        raise ValueError("Lead limit must be a positive integer.")

                csv_path = payload.get("csv_path")
                if csv_path is not None:
                    csv_path = str(csv_path).strip()
                if csv_path == "":
                    csv_path = None

                data, markdown, artifacts = self.orchestrator.run(
                    agent="lead",
                    csv_path=csv_path,
                    input_path=None if csv_path else path_from_root("agents", "lead_sourcing", "sample_input.json"),
                    limit=limit,
                    output_name=payload.get("output_name"),
                )
                summary = {
                    "headline": f"Leads returned: {len(data)}",
                    "subline": (
                        f"Top lead: {data[0]['company_name']} ({data[0]['priority_score']}/5)"
                        if data
                        else "No leads returned."
                    ),
                }
            elif agent == "research":
                selected_lead = payload.get("selected_lead")
                if selected_lead:
                    research_payload = {
                        "company_name": selected_lead.get("company_name", "Unknown company"),
                        "website_url": selected_lead.get("website", ""),
                        "notes": [
                            selected_lead.get("signal_detected", ""),
                            selected_lead.get("why_it_matters", ""),
                            selected_lead.get("likely_problem", ""),
                            selected_lead.get("notes", ""),
                        ],
                        "recommended_service_angle": selected_lead.get("suggested_angle", ""),
                        "sample_observation_for_outreach": selected_lead.get("likely_problem", ""),
                    }
                else:
                    research_payload = None

                data, markdown, artifacts = self.orchestrator.run(
                    agent="research",
                    input_path=None if research_payload else path_from_root("agents", "company_research", "sample_input.json"),
                    input_payload=research_payload,
                    output_name=payload.get("output_name") or "research-brief",
                )
                summary = {
                    "headline": f"Company: {data['company_name']}",
                    "subline": data["recommended_service_angle"],
                }
            else:
                data, markdown, artifacts = self.orchestrator.run(
                    agent="content",
                    input_path=path_from_root("agents", "content_repurposing", "sample_input.json"),
                    output_name=payload.get("output_name") or "content-output",
                )
                summary = {
                    "headline": f"Lane: {data['target_lane']}",
                    "subline": data["headline_options"][0],
                }
        except FileNotFoundError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(
            {
                "ok": True,
                "summary": summary,
                "json_path": str(artifacts.json_path),
                "markdown_path": str(artifacts.markdown_path),
                "markdown_preview": markdown[:1600],
                "data": data,
            }
        )

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_ui(host: str = "127.0.0.1", port: int = 8123) -> None:
    """Start the local Silent Agents server."""
    preferences_path = path_from_root("config", "preferences.json")
    if not preferences_path.exists():
        preferences_path = path_from_root("config", "preferences.example.json")

    sources_path = path_from_root("config", "sources.json")
    if not sources_path.exists():
        sources_path = path_from_root("config", "sources.example.json")

    server = ThreadingHTTPServer((host, port), SilentAgentsHandler)
    server.orchestrator = AgentOrchestrator(  # type: ignore[attr-defined]
        preferences_path=preferences_path,
        sources_path=sources_path,
        output_dir=default_output_dir(),
    )
    print(f"Silent Agents UI running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Silent Agents UI.")
    finally:
        server.server_close()
