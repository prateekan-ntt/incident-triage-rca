from __future__ import annotations

import sys

from .agent import IncidentTriageAgent
from .llm import LLMProvider, OllamaProvider
from .scenarios import SCENARIOS


CAUSE_ALIASES = {
    "bad deployment": (
        "bad deployment", "deployment regression", "release regression", "bad release",
        "orders-api-v42", "change in v42",
    ),
    "database connection pool exhaustion": (
        "database connection pool exhaustion", "database connection pool", "connection pool exhaustion",
        "connection pool exhausted", "connection pool max connections", "database pool", "max_connections",
    ),
    "certificate expiry": (
        "certificate expiry", "certificate expired", "certificate expiration", "expired certificate", "tls certificate",
    ),
    "upstream third-party outage": (
        "upstream third-party outage", "third-party outage", "merchant-gateway", "payment-gateway upstream",
        "payment provider outage",
    ),
    "memory leak": ("memory leak", "out of memory", "oom", "heap growth"),
    "config drift": (
        "config drift", "configuration drift", "feature flag mismatch", "feature flag drift",
        "feature flag misconfiguration", "drift detection", "feature flag propagation delay",
    ),
    "noisy neighbor (resource contention)": (
        "noisy neighbor", "resource contention", "shared-node contention", "shared node workload",
    ),
}


def _canonical_cause(value: str) -> str:
    normalized = value.casefold()
    for cause, aliases in CAUSE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return cause
    return normalized.strip()


def evaluate(provider: LLMProvider | None = None, progress: bool = False) -> dict:
    results = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        if progress:
            print(f"[{index}/{len(SCENARIOS)}] Evaluating {scenario['id']} with Qwen3...", file=sys.stderr, flush=True)
        agent = IncidentTriageAgent(provider=provider or OllamaProvider(), scenario_id=scenario["id"])
        try:
            incident = agent.correlate_alerts(scenario["alerts"])
        except RuntimeError as error:
            results.append({
                "scenario": scenario["id"],
                "top1": False,
                "top3": False,
                "root_services": sorted({alert["service"] for alert in scenario["alerts"]}),
                "hypotheses": [],
                "tool_calls": 0,
                "citation_count": 0,
                "valid_citation_count": 0,
                "evidence_citation_correctness": 0.0,
                "predicted_alert_clusters": [],
                "error": str(error),
            })
            continue
        expected_cause = _canonical_cause(scenario["root_cause"])
        ranked_causes = [_canonical_cause(hyp.name) for hyp in incident.hypotheses]
        evidence_events = [event for event in incident.trace if event.get("type") == "evidence_retrieved"]
        valid_evidence_ids = {
            item["id"]
            for event in evidence_events
            for item in event.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        citations = incident.citations
        valid_citations = sum(
            1 for citation in citations
            if any(citation.startswith(f"{evidence_id}:") for evidence_id in valid_evidence_ids)
        )
        call_count = sum(1 for event in incident.trace if event.get("type") == "tool_call")
        results.append({
            "scenario": scenario["id"],
            "top1": bool(ranked_causes and ranked_causes[0] == expected_cause),
            "top3": expected_cause in ranked_causes[:3],
            "root_services": incident.root_services,
            "hypotheses": [hyp.name for hyp in incident.hypotheses],
            "tool_calls": call_count,
            "citation_count": len(citations),
            "valid_citation_count": valid_citations,
            "evidence_citation_correctness": valid_citations / len(citations) if citations else 0.0,
            "predicted_alert_clusters": incident.alert_clusters,
        })

    top1_accuracy = sum(1 for item in results if item["top1"]) / len(results)
    top3_accuracy = sum(1 for item in results if item["top3"]) / len(results)
    citation_total = sum(item["citation_count"] for item in results)
    citation_valid = sum(item["valid_citation_count"] for item in results)
    tool_call_total = sum(item["tool_calls"] for item in results)

    true_positive_pairs = 0
    predicted_positive_pairs = 0
    for scenario, result in zip(SCENARIOS, results):
        expected_groups = scenario.get("expected_alert_groups", [list(range(len(scenario["alerts"])))])
        expected_by_alert = {
            alert_index: group_index
            for group_index, group in enumerate(expected_groups)
            for alert_index in group
        }
        predicted_by_alert = {
            alert_index: group_index
            for group_index, group in enumerate(result["predicted_alert_clusters"])
            for alert_index in group
        }
        alert_count = len(scenario["alerts"])
        for left in range(alert_count):
            for right in range(left + 1, alert_count):
                if predicted_by_alert.get(left) == predicted_by_alert.get(right):
                    predicted_positive_pairs += 1
                    if expected_by_alert.get(left) == expected_by_alert.get(right):
                        true_positive_pairs += 1

    summary = {
        "total_scenarios": len(results),
        "root_cause_accuracy_top1": top1_accuracy,
        "root_cause_accuracy_top3": top3_accuracy,
        "alert_correlation_precision": (
            true_positive_pairs / predicted_positive_pairs if predicted_positive_pairs else None
        ),
        "evidence_citation_correctness": citation_valid / citation_total if citation_total else 0.0,
        "mean_tool_calls_per_incident": tool_call_total / len(results),
        "unsafe_action_rate": 0.0,
        "unsafe_action_metric_note": "No remediation executor is implemented; this run executed no actions.",
        "failed_scenario_count": sum(1 for item in results if "error" in item),
        "results": results,
    }
    return summary
