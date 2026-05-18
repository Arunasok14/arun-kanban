"""
Policy engine — evaluates agent permission prompts against rules before
routing to human approval (Sprint 6).

Actions:
  deny  — immediately refuse, write "n\n" to stdin, emit system log
  warn  — escalate to human approval (Sprint 2 flow)
  allow — no policy match, proceed normally

Default policies are built in; the runtime-manager can also fetch
user-defined policies from the API at evaluation time.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PolicyResult:
    action: str   # "allow" | "warn" | "deny"
    message: str = ""
    policy_id: Optional[str] = None


# ── Built-in default policies ─────────────────────────────────────────────────
# Ordered: first match wins.

DEFAULT_POLICIES: list[dict] = [
    # Block dropping non-test/temp tables
    {
        "id": "no-drop-prod-table",
        "pattern": r"DROP\s+TABLE\s+(?!test_|tmp_|temp_)\w+",
        "action": "deny",
        "message": "Dropping production tables is not allowed by policy.",
    },
    # Block deleting files outside /workspace (Docker paths)
    {
        "id": "no-rm-outside-workspace",
        "pattern": r"rm\s+(-[rRf]+\s+)+/(?!workspace)\S*",
        "action": "deny",
        "message": "Deleting files outside the workspace directory is not allowed.",
    },
    # Block git push --force to protected branch patterns
    {
        "id": "no-force-push",
        "pattern": r"git\s+push\b.*--force\b",
        "action": "warn",
        "message": "Force push detected — requires explicit approval.",
    },
    # Warn on curl/wget piped to shell (supply-chain risk)
    {
        "id": "no-remote-pipe-shell",
        "pattern": r"(curl|wget)\s+.*\|\s*(ba)?sh",
        "action": "warn",
        "message": "Downloading and executing remote scripts requires approval.",
    },
    # Block chmod 777
    {
        "id": "no-chmod-777",
        "pattern": r"chmod\s+(-[Rr]+\s+)?777",
        "action": "deny",
        "message": "Setting world-writable permissions (777) is not allowed.",
    },
]


def evaluate(
    prompt_text: str,
    extra_policies: Optional[list[dict]] = None,
) -> PolicyResult:
    """
    Evaluate *prompt_text* against all active policies.
    *extra_policies* are user-defined policies fetched from the API.
    Returns the first matching PolicyResult, or allow if no match.
    """
    all_policies = list(DEFAULT_POLICIES) + (extra_policies or [])
    for policy in all_policies:
        if not policy.get("enabled", True):
            continue
        pattern = policy.get("pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, prompt_text, re.IGNORECASE | re.MULTILINE):
                return PolicyResult(
                    action=policy.get("action", "warn"),
                    message=policy.get("message", "Blocked by policy."),
                    policy_id=policy.get("id"),
                )
        except re.error:
            pass  # skip malformed patterns

    return PolicyResult(action="allow")
