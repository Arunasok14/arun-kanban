"""
Embedding service for context persistence (Sprint 5).

Embeds task/execution summaries as vectors and retrieves similar prior work
to inject as context into new task executions.

Embedding backend (in priority order):
  1. OpenAI text-embedding-3-small — if openai_api_key is set in settings
  2. Fallback: no embeddings — retrieve by recency only (last N records)

Vector storage: sqlite-vec extension (vec0 virtual table).
If sqlite-vec is not installed/loadable, falls back to recency retrieval.
"""
from __future__ import annotations
import json
import struct
from typing import Optional
import aiosqlite

from ..schemas import utcnow, new_id

# sqlite-vec availability flag (set at first load attempt)
_vec_available: Optional[bool] = None


def _try_load_vec(db_conn) -> bool:
    """Attempt to load sqlite-vec extension. Returns True on success."""
    global _vec_available
    if _vec_available is not None:
        return _vec_available
    try:
        import sqlite_vec  # type: ignore
        db_conn.enable_load_extension(True)
        sqlite_vec.load(db_conn)
        db_conn.enable_load_extension(False)
        _vec_available = True
    except Exception:
        _vec_available = False
    return _vec_available


def _serialize_vec(floats: list[float]) -> bytes:
    """Serialize a list of floats to little-endian IEEE 754 bytes for sqlite-vec."""
    return struct.pack(f"{len(floats)}f", *floats)


async def _embed_openai(text: str, api_key: str) -> list[float]:
    """Call OpenAI text-embedding-3-small. Returns 1536-dim vector."""
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"input": text, "model": "text-embedding-3-small"},
        )
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]


async def embed(text: str, api_key: str = "") -> Optional[list[float]]:
    """
    Generate an embedding for *text*.
    Returns None if no embedding backend is available.
    """
    if api_key.strip():
        try:
            return await _embed_openai(text, api_key)
        except Exception as e:
            print(f"[embedding] OpenAI embed failed: {e}")
    return None


def _detect_regression_type(
    outcome: str, test_results: Optional[dict], error_message: str = ""
) -> tuple[Optional[str], Optional[str]]:
    """
    Infer regression_type and error_pattern from execution outcome.
    Returns (regression_type, error_pattern) or (None, None).
    """
    if outcome != "failure":
        return None, None

    if test_results and (test_results.get("failed", 0) > 0 or test_results.get("errors", 0) > 0):
        # Extract first failing test name from details list
        details = test_results.get("details", [])
        error_pattern = details[0][:80] if details else None
        return "test_failure", error_pattern

    if "budget" in error_message.lower():
        return "budget_exhausted", None

    if "timeout" in error_message.lower():
        return "timeout", None

    return "build_failure", None


async def record_execution(
    db: aiosqlite.Connection,
    task_id: str,
    execution_id: str,
    task_title: str,
    task_description: str,
    outcome: str,  # "success" | "failure"
    test_results: Optional[dict],
    api_key: str = "",
    error_message: str = "",
) -> None:
    """
    Persist a context record for a completed/failed execution.
    Stores a prose summary, regression metadata, and (if possible) an embedding vector.
    """
    content = (
        f"Task: {task_title}\n"
        f"Description: {task_description or '(none)'}\n"
        f"Outcome: {outcome}"
    )
    if test_results:
        p, f, e = test_results.get("passed", 0), test_results.get("failed", 0), test_results.get("errors", 0)
        content += f"\nTests: {p} passed, {f} failed, {e} errors"

    regression_type, error_pattern = _detect_regression_type(outcome, test_results, error_message)

    record_id = new_id()
    now = utcnow()

    await db.execute(
        """INSERT OR IGNORE INTO context_records
           (id, task_id, execution_id, content, outcome, test_results,
            regression_type, error_pattern, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_id,
            task_id,
            execution_id,
            content,
            outcome,
            json.dumps(test_results) if test_results else None,
            regression_type,
            error_pattern,
            now,
        ),
    )
    await db.commit()

    # Try to store vector embedding
    vec = await embed(content, api_key)
    if vec is not None:
        try:
            # Get the rowid of the just-inserted context_record
            async with db.execute(
                "SELECT rowid FROM context_records WHERE id = ?", (record_id,)
            ) as cur:
                row = await cur.fetchone()
            if row:
                rowid = row[0]
                # Check if vec table is available (raw connection needed for extension)
                await db.execute(
                    "INSERT INTO context_embeddings (rowid, embedding) VALUES (?, ?)",
                    (rowid, _serialize_vec(vec)),
                )
                await db.commit()
        except Exception as e:
            print(f"[embedding] Failed to store vector: {e}")


async def retrieve_similar(
    db: aiosqlite.Connection,
    query_text: str,
    k: int = 5,
    api_key: str = "",
) -> list[dict]:
    """
    Return up to *k* context records most similar to *query_text*.
    Falls back to most-recent records when embeddings are unavailable.
    """
    # Try vector search first
    query_vec = await embed(query_text, api_key)
    if query_vec is not None:
        try:
            async with db.execute(
                """SELECT cr.task_id, cr.content, cr.outcome, cr.test_results, cr.created_at
                   FROM context_embeddings ce
                   JOIN context_records cr ON ce.rowid = cr.rowid
                   WHERE ce.embedding MATCH ?
                     AND k = ?
                   ORDER BY distance""",
                (_serialize_vec(query_vec), k),
            ) as cur:
                rows = await cur.fetchall()
            if rows:
                return [_row_to_dict(r) for r in rows]
        except Exception as e:
            print(f"[embedding] Vector search failed, using recency fallback: {e}")

    # Fallback: most recent records
    async with db.execute(
        """SELECT task_id, content, outcome, test_results, created_at
           FROM context_records
           ORDER BY created_at DESC
           LIMIT ?""",
        (k,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("test_results") and isinstance(d["test_results"], str):
        try:
            d["test_results"] = json.loads(d["test_results"])
        except Exception:
            d["test_results"] = None
    return d
