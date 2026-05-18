from __future__ import annotations
import asyncio
import os
import re
from pathlib import Path
from typing import Optional
from .config import settings


class WorktreeManager:
    def __init__(self, workspaces_root: Optional[str] = None):
        self._root = Path(workspaces_root or settings.workspaces_root).resolve()

    def worktree_path(self, project_name: str, task_id: str) -> Path:
        safe_name = re.sub(r"[^a-z0-9_-]", "-", project_name.lower())
        return self._root / safe_name / f"task-{task_id}"

    def branch_name(self, task_id: str, task_title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", task_title.lower()).strip("-")[:40]
        return f"task/{task_id[:8]}-{slug}"

    async def _run_git(self, args: list[str], cwd: str) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def create_worktree(
        self,
        repo_path: str,
        project_name: str,
        task_id: str,
        task_title: str,
        base_branch: str = "main",
    ) -> tuple[str, str]:
        """Returns (worktree_path_str, branch_name)."""
        branch = self.branch_name(task_id, task_title)
        dest = self.worktree_path(project_name, task_id)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # If worktree directory already exists (from a prior run), reuse it
        if dest.exists():
            return str(dest), branch

        rc, _, err = await self._run_git(
            ["worktree", "add", "-b", branch, str(dest), base_branch],
            cwd=repo_path,
        )
        if rc != 0:
            # Branch already exists but directory doesn't — check out without -b
            rc2, _, err2 = await self._run_git(
                ["worktree", "add", str(dest), branch],
                cwd=repo_path,
            )
            if rc2 != 0:
                raise RuntimeError(f"git worktree add failed: {err}\n{err2}")

        return str(dest), branch

    async def remove_worktree(self, repo_path: str, worktree_path: str) -> None:
        rc, _, err = await self._run_git(
            ["worktree", "remove", "--force", worktree_path],
            cwd=repo_path,
        )
        if rc != 0:
            raise RuntimeError(f"git worktree remove failed: {err}")

    async def commit_changes(
        self,
        worktree_path: str,
        message: str,
    ) -> Optional[str]:
        """Stages all changes and commits. Returns commit SHA or None if clean."""
        rc, status_out, _ = await self._run_git(["status", "--porcelain"], cwd=worktree_path)
        if not status_out.strip():
            return None

        await self._run_git(["add", "-A"], cwd=worktree_path)

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "AI Agent",
            "GIT_AUTHOR_EMAIL": "agent@kanban-control-plane.local",
            "GIT_COMMITTER_NAME": "AI Agent",
            "GIT_COMMITTER_EMAIL": "agent@kanban-control-plane.local",
        }
        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", message,
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        await proc.communicate()

        rc, sha, _ = await self._run_git(["rev-parse", "HEAD"], cwd=worktree_path)
        return sha.strip() if rc == 0 else None

    async def get_diff(self, worktree_path: str, base_branch: str) -> str:
        _, diff, _ = await self._run_git(
            ["diff", base_branch, "HEAD"],
            cwd=worktree_path,
        )
        return diff

    async def get_diff_stat(self, worktree_path: str, base_branch: str) -> str:
        """Return a short --stat summary of changes vs base_branch."""
        _, stat, _ = await self._run_git(
            ["diff", "--stat", f"{base_branch}...HEAD"],
            cwd=worktree_path,
        )
        return stat.strip()

    async def push_branch(
        self,
        worktree_path: str,
        branch_name: str,
        remote: str = "origin",
    ) -> bool:
        """Push *branch_name* to *remote*. Returns True on success."""
        rc, _, err = await self._run_git(
            ["push", "--set-upstream", remote, branch_name],
            cwd=worktree_path,
        )
        if rc != 0:
            print(f"[worktree] git push failed: {err}")
        return rc == 0
