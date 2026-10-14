from incident_triage_agent.agent import CorrelatedIncident, IncidentTriageAgent


class StubProvider:
    prompt = ""

    def generate(self, prompt, schema=None):
        self.prompt = prompt
        return {
            "hypotheses": [
                {
                    "name": "Database connection pool exhaustion",
                    "confidence": 0.8,
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                },
                {
                    "name": "Bad deployment",
                    "confidence": 0.5,
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                },
                {
                    "name": "Upstream third-party outage",
                    "confidence": 0.2,
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                },
            ]
        }


def test_incident_agent_builds_incident_and_top_hypothesis():
    agent = IncidentTriageAgent(provider=StubProvider())
    incident = agent.correlate_alerts([
        {"service": "orders-api", "severity": "critical", "message": "HTTP 500 on checkout", "timestamp": "2026-01-01T10:00:00Z"},
        {"service": "orders-db", "severity": "critical", "message": "db pool saturated", "timestamp": "2026-01-01T10:00:05Z"},
        {"service": "payments-api", "severity": "warning", "message": "timeouts", "timestamp": "2026-01-01T10:00:10Z"},
    ])
    assert isinstance(incident, CorrelatedIncident)
    assert incident.root_services
    assert len(incident.hypotheses) == 3
    assert incident.hypotheses[0].name == "Database connection pool exhaustion"
    assert any(event["type"] == "evidence_retrieved" for event in incident.trace)
    assert len([event for event in incident.trace if event["type"] == "tool_call"]) <= agent.MAX_TOOL_CALLS
    assert "pass123" not in agent.provider.prompt
    assert "run rollback on all services" not in agent.provider.prompt.lower()
    assert "developer override" not in agent.provider.prompt.lower()


def test_alerts_cluster_by_dependency_and_five_minute_window():
    agent = IncidentTriageAgent(provider=StubProvider())
    clustered = agent._cluster_alerts([
        {"service": "orders-api", "timestamp": "2026-01-01T10:00:00Z"},
        {"service": "orders-db", "timestamp": "2026-01-01T10:04:00Z"},
        {"service": "auth-api", "timestamp": "2026-01-01T10:00:00Z"},
        {"service": "reporting-job", "timestamp": "2026-01-01T10:10:00Z"},
    ])
    assert clustered == [[0, 1], [2], [3]]


def test_runbook_actions_are_tiered_and_never_auto_executed():
    agent = IncidentTriageAgent(provider=StubProvider(), scenario_id="db_pool_exhaustion")
    incident = agent.correlate_alerts([
        {"service": "orders-db", "severity": "critical", "message": "connection pool saturation", "timestamp": "2026-01-01T10:00:00Z"},
        {"service": "orders-api", "severity": "warning", "message": "timeouts on checkout", "timestamp": "2026-01-01T10:00:03Z"},
    ])
    assert incident.remediation_plan
    assert incident.remediation_plan[0]["safety_tier"] == "Risky"
    assert incident.remediation_plan[0]["requires_human_approval"]
    assert incident.remediation_plan[0]["requires_justification"]
    assert incident.remediation_plan[0]["execution_status"] == "never_executed_by_agent"


def test_low_confidence_generates_specific_questions():
    questions = IncidentTriageAgent._clarifying_questions(0.45, [])
    assert questions
    assert "deployment" in questions[0].lower()


def test_model_paraphrases_map_to_risky_remediation_proposals():
    deployment = IncidentTriageAgent._build_remediation_plan(
        "Checkout handler change in orders-api-v42 caused increased HTTP 500 errors", []
    )
    upstream = IncidentTriageAgent._build_remediation_plan(
        "Third-party merchant-gateway outage", []
    )
    assert deployment[0]["action"] == "rollback release"
    assert deployment[0]["safety_tier"] == "Risky"
    assert upstream[0]["action"] == "failover gateway"
    assert upstream[0]["safety_tier"] == "Risky"


def test_scenario_injection_attempts_are_removed_before_provider_call():
    provider = StubProvider()
    agent = IncidentTriageAgent(provider=provider, scenario_id="red_herring")
    agent.correlate_alerts([
        {"service": "orders-api", "severity": "critical", "message": "checkout failing", "timestamp": "2026-01-01T10:00:00Z"}
    ])

    assert "DEVELOPER OVERRIDE" not in provider.prompt
    assert "ignore previous instructions" not in provider.prompt.lower()
    assert "delete_data" not in provider.prompt


def test_alert_secrets_are_masked_in_model_prompt_and_report_timeline():
    provider = StubProvider()
    agent = IncidentTriageAgent(provider=provider)
    incident = agent.correlate_alerts([
        {
            "service": "orders-api",
            "severity": "critical",
            "message": "checkout failing; DB_URL=postgresql://user:alert-secret@db.test/app",
            "timestamp": "2026-01-01T10:00:00Z",
        }
    ])

    assert "alert-secret" not in provider.prompt
    assert "alert-secret" not in str(incident.timeline)
