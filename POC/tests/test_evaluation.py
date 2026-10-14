from incident_triage_agent.evaluation import _canonical_cause, evaluate
from tests.test_agent import StubProvider


class FailingProvider:
    def generate(self, prompt, schema=None):
        raise RuntimeError("synthetic model failure")


def test_canonical_cause_maps_model_paraphrases_to_expected_classes():
    assert _canonical_cause("checkout handler in orders-api-v42 introduced HTTP 500 errors") == "bad deployment"
    assert _canonical_cause("database connection pool exhaustion during checkout flow") == "database connection pool exhaustion"
    assert _canonical_cause("Certificate expiration for auth-service.internal") == "certificate expiry"
    assert _canonical_cause("payment-gateway upstream connection refused") == "upstream third-party outage"


def test_evaluation_computes_metrics_from_stubbed_agent_runs():
    result = evaluate(provider=StubProvider())

    assert result["total_scenarios"] == 8
    assert result["root_cause_accuracy_top1"] == 0.25
    assert result["root_cause_accuracy_top3"] == 0.5
    assert result["evidence_citation_correctness"] == 0.0
    assert result["mean_tool_calls_per_incident"] > 0
    assert result["unsafe_action_rate"] == 0.0


def test_evaluation_records_model_failures_and_continues():
    result = evaluate(provider=FailingProvider())

    assert result["total_scenarios"] == 8
    assert result["failed_scenario_count"] == 8
    assert result["root_cause_accuracy_top1"] == 0.0
    assert all("error" in scenario for scenario in result["results"])