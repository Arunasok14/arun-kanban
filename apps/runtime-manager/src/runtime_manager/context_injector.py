from __future__ import annotations
from pathlib import Path
from typing import Optional

TEMPLATE = """\
# Task Context

## Task ID
{task_id}

## Title
{title}

## Description
{description}

{prior_work_section}\
## Instructions
You are an AI coding agent running inside a git worktree. Complete the task described above.

Guidelines:
- Work within this worktree directory only
- Make targeted, focused changes to accomplish the task
- Do not ask for clarification — make reasonable assumptions and proceed
- If you cannot complete a subtask, leave a TODO comment explaining why
- After completing your work, the system will auto-commit your changes

## Repository Information
- Branch: {branch_name}
- Base branch: {base_branch}
- Worktree path: {worktree_path}
"""


def _build_prior_work_section(prior_work: list[dict]) -> str:
    """Render the ## Prior Work section, including regression warnings."""
    if not prior_work:
        return ""

    # Separate successes from failures/regressions
    regressions = [r for r in prior_work if r.get("outcome") != "success"]
    successes = [r for r in prior_work if r.get("outcome") == "success"]

    lines: list[str] = []

    # ── Regression warnings (shown first, prominently) ────────────────────────
    if regressions:
        lines.append("## ⚠️ Regression Warnings\n")
        lines.append(
            "These similar tasks previously failed. "
            "Take extra care to avoid the same issues:\n"
        )
        for rec in regressions[:3]:
            regression_type = rec.get("regression_type", "failure")
            error_pattern = rec.get("error_pattern")
            content = rec.get("content", "")
            snippet = content[:150].replace("\n", " ")

            if regression_type == "test_failure" and error_pattern:
                lines.append(
                    f"- ✗ **Test failure**: `{error_pattern}` — {snippet}"
                )
            else:
                label = {
                    "build_failure": "Build failure",
                    "timeout": "Timeout",
                    "budget_exhausted": "Budget exhausted",
                }.get(regression_type, "Failure")
                lines.append(f"- ✗ **{label}**: {snippet}")
        lines.append("")

    # ── Prior successes ───────────────────────────────────────────────────────
    if successes:
        lines.append("## Prior Work\n")
        lines.append(
            "The following similar tasks completed successfully. "
            "Use them as reference:\n"
        )
        for rec in successes[:3]:
            content = rec.get("content", "")
            snippet = content[:200].replace("\n", " ")
            lines.append(f"- ✓ {snippet}")
            tr = rec.get("test_results")
            if tr and isinstance(tr, dict):
                p, f = tr.get("passed", 0), tr.get("failed", 0)
                lines.append(f"  Tests: {p} passed, {f} failed")
        lines.append("")

    return "\n".join(lines) + "\n"


class ContextInjector:
    def inject(
        self,
        worktree_path: str,
        task_id: str,
        title: str,
        description: str,
        branch_name: str,
        base_branch: str,
        prior_work: Optional[list[dict]] = None,
    ) -> str:
        """Writes TASK_CONTEXT.md to the worktree and returns the prompt string."""
        prior_work_section = _build_prior_work_section(prior_work or [])
        content = TEMPLATE.format(
            task_id=task_id,
            title=title,
            description=description or "(no description provided)",
            prior_work_section=prior_work_section,
            branch_name=branch_name,
            base_branch=base_branch,
            worktree_path=worktree_path,
        )
        ctx_file = Path(worktree_path) / "TASK_CONTEXT.md"
        ctx_file.write_text(content, encoding="utf-8")
        return content.strip()
