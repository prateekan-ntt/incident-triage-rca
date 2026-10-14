from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import IncidentTriageAgent
from .evaluation import evaluate
from .scenarios import SCENARIOS


def _scenario_lookup(name: str):
    for scenario in SCENARIOS:
        if scenario["id"] == name:
            return scenario
    raise ValueError(f"Unknown scenario '{name}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Incident Triage Agent POC")
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument("--scenario", help="Scenario ID to run", default=None)
    run_mode.add_argument("--alerts-file", help="Path to JSON array of alerts for an unseen incident")
    run_mode.add_argument("--evaluate", action="store_true", help="Run the evaluation harness")
    args = parser.parse_args()

    if args.evaluate:
        print(json.dumps(evaluate(progress=True), indent=2))
        return

    if args.scenario:
        scenario = _scenario_lookup(args.scenario)
        agent = IncidentTriageAgent(scenario_id=scenario["id"])
        alerts = scenario["alerts"]
        scenario_id = scenario["id"]
        expected_root_cause = scenario["root_cause"]
    elif args.alerts_file:
        data = json.loads(Path(args.alerts_file).read_text(encoding="utf-8"))
        alerts = data.get("alerts") if isinstance(data, dict) else data
        if not isinstance(alerts, list) or not all(isinstance(item, dict) for item in alerts):
            parser.error("--alerts-file must contain a JSON array of alert objects or an object with an alerts array")
        agent = IncidentTriageAgent()
        scenario_id = "custom"
        expected_root_cause = None
    else:
        print("No action specified. Use --scenario <id>, --alerts-file <path>, or --evaluate.")
        return

    incident = agent.correlate_alerts(alerts)
    print(json.dumps({
        "scenario_id": scenario_id,
        "expected_root_cause": expected_root_cause,
        "detected_root_services": incident.root_services,
        "affected_services": incident.affected_services,
        "blast_radius": incident.blast_radius,
        "timeline": incident.timeline,
        "alert_clusters": incident.alert_clusters,
        "top_hypotheses": [
            {"name": h.name, "confidence": h.confidence, "evidence": h.evidence}
            for h in incident.hypotheses[:3]
        ],
        "summary": incident.summary,
        "citations": incident.citations,
        "remediation_plan": incident.remediation_plan,
        "clarifying_questions": incident.clarifying_questions,
        "post_incident_rca": incident.post_incident_rca,
        "trace": incident.trace,
    }, indent=2))


if __name__ == "__main__":
    main()
