SCENARIOS = [
    {
        "id": "bad_deployment",
        "root_cause": "Bad deployment",
        "service": "orders-api",
        "alerts": [
            {"service": "orders-api", "severity": "critical", "message": "checkout latency spike", "timestamp": "2026-01-01T10:00:00Z"},
            {"service": "orders-api", "severity": "critical", "message": "HTTP 500 in payment flow", "timestamp": "2026-01-01T10:00:05Z"},
        ],
        "evidence": [
            "orders-api v42 deployed at 09:50Z",
            "error rate increased from 0.2 to 0.82",
        ],
    },
    {
        "id": "db_pool_exhaustion",
        "root_cause": "Database connection pool exhaustion",
        "service": "orders-db",
        "alerts": [
            {"service": "orders-db", "severity": "critical", "message": "connection pool saturation", "timestamp": "2026-01-01T10:00:00Z"},
            {"service": "orders-api", "severity": "warning", "message": "timeouts on checkout", "timestamp": "2026-01-01T10:00:03Z"},
        ],
        "evidence": [
            "orders-db pool utilization 97%",
            "max_connections exceeded",
        ],
    },
    {
        "id": "certificate_expiry",
        "root_cause": "Certificate expiry",
        "service": "auth-api",
        "alerts": [
            {"service": "auth-api", "severity": "critical", "message": "tls handshake failure", "timestamp": "2026-01-01T10:00:02Z"},
        ],
        "evidence": [
            "certificate expired for auth-service.internal",
            "tls_expiry_days = 2",
        ],
    },
    {
        "id": "third_party_outage",
        "root_cause": "Upstream third-party outage",
        "service": "payment-gateway",
        "alerts": [
            {"service": "payment-gateway", "severity": "critical", "message": "merchant-gateway timeout", "timestamp": "2026-01-01T10:00:01Z"},
            {"service": "orders-api", "severity": "warning", "message": "payment checks failing", "timestamp": "2026-01-01T10:00:04Z"},
        ],
        "evidence": [
            "merchant-gateway timeout",
            "upstream dependency timeout",
        ],
    },
    {
        "id": "memory_leak",
        "root_cause": "Memory leak",
        "service": "batch-ingest",
        "alerts": [
            {"service": "batch-ingest", "severity": "critical", "message": "OOM detected", "timestamp": "2026-01-01T10:00:00Z"},
        ],
        "evidence": [
            "memory usage 92%",
            "out of memory after 18h runtime",
        ],
    },
    {
        "id": "config_drift",
        "root_cause": "Config drift",
        "service": "catalog-service",
        "alerts": [
            {"service": "catalog-service", "severity": "warning", "message": "feature flag mismatch", "timestamp": "2026-01-01T10:00:00Z"},
        ],
        "evidence": [
            "feature flag changed from false to true",
            "config drift observed",
        ],
    },
    {
        "id": "noisy_neighbor",
        "root_cause": "Noisy neighbor (resource contention)",
        "service": "orders-api",
        "alerts": [
            {"service": "orders-api", "severity": "warning", "message": "latency spike in checkout", "timestamp": "2026-01-01T10:00:00Z"},
            {"service": "user-gateway", "severity": "warning", "message": "queue backlog increase", "timestamp": "2026-01-01T10:00:05Z"},
        ],
        "evidence": [
            "queue backlog increase from 2k to 12k messages",
            "noise and contention across services",
        ],
    },
    {
        "id": "red_herring",
        "root_cause": "Database connection pool exhaustion",
        "service": "orders-api",
        "alerts": [
            {"service": "orders-api", "severity": "critical", "message": "checkout failing", "timestamp": "2026-01-01T10:00:00Z"},
            {"service": "inventory-api", "severity": "warning", "message": "inventory read latency", "timestamp": "2026-01-01T10:00:04Z"},
        ],
        "evidence": [
            "initial suspect was orders-api deployment",
            "root cause was actually database pool exhaustion",
        ],
    },
]
