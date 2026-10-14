import re

INJECTION_PATTERNS = [
    r"(?i)\b(?:SYSTEM|DEVELOPER|ADMIN|POLICY|AI|BOT)(?:\s+OVERRIDE)?\s*:\s*.*$",
    r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b.*$",
]

SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)(?:password|passwd|pwd|secret|api[_-]?key|token|session[_-]?key)\s*[:=]\s*([^\s;]+)"), "[MASKED]"),
    (re.compile(r"(?i)(?:db_url|jdbc\s*[:=]\s*|postgresql://|mongodb://|redis://|amqp://|https?://)[^\s;]+"), "[MASKED]"),
    (re.compile(r"(?i)(?:aws_access_key_id|aws_secret_access_key|x-amz-security-token)\s*[:=]\s*([^\s;]+)"), "[MASKED]"),
]

ACTION_CLASSIFIER = {
    "delete_data": "Forbidden",
    "drop_table": "Forbidden",
    "purge_queue": "Forbidden",
    "disable_auth": "Forbidden",
    "rollback_release": "Risky",
    "change_config": "Risky",
    "drain_node": "Risky",
    "scale_database_pool": "Risky",
    "renew_certificate": "Risky",
    "failover_gateway": "Risky",
    "restart_pod": "Safe",
    "restart_worker": "Safe",
    "clear_cache": "Safe",
    "flush_cache": "Safe",
}


def mask_sensitive_data(text: str) -> str:
    masked = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def sanitize_log_text(text: str) -> str:
    safe_lines = []
    for line in text.splitlines():
        if any(re.search(pattern, line) for pattern in INJECTION_PATTERNS):
            continue
        safe_lines.append(line)
    return re.sub(r"\s+", " ", " ".join(safe_lines)).strip()


def sanitize_untrusted_value(value):
    if isinstance(value, str):
        return mask_sensitive_data(sanitize_log_text(value))
    if isinstance(value, dict):
        return {key: sanitize_untrusted_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_untrusted_value(item) for item in value]
    return value


def classify_action(action_name: str) -> str:
    normalized = action_name.strip().lower().replace("-", "_").replace(" ", "_")
    return ACTION_CLASSIFIER.get(normalized, "Forbidden")


def authorize_action(
    action_name: str,
    human_approved: bool = False,
    justification: str = "",
) -> dict[str, str | bool]:
    tier = classify_action(action_name)
    if tier == "Forbidden":
        return {"tier": tier, "authorized": False, "reason": "Forbidden actions can never be authorized."}
    if not human_approved:
        return {"tier": tier, "authorized": False, "reason": "Human confirmation is required."}
    if tier == "Risky" and not justification.strip():
        return {"tier": tier, "authorized": False, "reason": "Risky actions require a written justification."}
    return {"tier": tier, "authorized": True, "reason": "Human approval requirements are satisfied; no action is executed by this POC."}
