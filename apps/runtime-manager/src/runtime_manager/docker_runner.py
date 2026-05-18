"""
Docker sandbox runner for agent executions.

Each agent runs inside a container with:
- Worktree mounted at /workspace (rw)
- Resource limits (memory + CPU)
- Network access (bridge) for API calls, or "none" for full isolation
- ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY injected via env

Requires: pip install docker
Requires: Docker Desktop or Docker Engine running on the host.
"""
from __future__ import annotations
import asyncio
import os
from typing import AsyncGenerator

DOCKER_IMAGE = "kanban-agent:latest"


async def run_in_container(
    command: list[str],
    worktree_path: str,
    env: dict[str, str],
    image: str = DOCKER_IMAGE,
    mem_limit: str = "2g",
    cpu_quota: int = 50000,  # 50% of one core (100000 = 100%)
    network_mode: str = "bridge",
) -> AsyncGenerator[bytes, None]:
    """
    Run *command* inside a Docker container and stream stdout+stderr as raw bytes.

    Yields chunks as they arrive from the container log stream.
    """
    try:
        import docker as docker_sdk  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "docker package not installed — run: pip install docker"
        ) from exc

    client = docker_sdk.from_env()

    # Ensure the worktree exists on the host before mounting
    os.makedirs(worktree_path, exist_ok=True)

    loop = asyncio.get_event_loop()

    def _run() -> list[bytes]:
        """Blocking call — runs in a thread pool executor."""
        container = client.containers.run(
            image,
            command,
            volumes={worktree_path: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            environment=env,
            mem_limit=mem_limit,
            cpu_quota=cpu_quota,
            network_mode=network_mode,
            detach=True,
            remove=False,  # we remove manually after draining logs
        )
        chunks: list[bytes] = []
        try:
            for chunk in container.logs(stream=True, follow=True):
                chunks.append(chunk)
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
        return chunks

    # Run the blocking Docker call in a thread so it doesn't block the event loop
    chunks = await loop.run_in_executor(None, _run)
    return _chunks_generator(chunks)


def _chunks_generator(chunks: list[bytes]):
    """Sync generator — only used as an async adapter."""
    yield from chunks


async def stream_container(
    command: list[str],
    worktree_path: str,
    env: dict[str, str],
    image: str = DOCKER_IMAGE,
    mem_limit: str = "2g",
    cpu_quota: int = 50000,
    network_mode: str = "bridge",
) -> AsyncGenerator[str, None]:
    """
    Higher-level wrapper: yields decoded text lines from the container.
    Handles Docker log multiplexing (stdout/stderr prefix bytes).
    """
    try:
        import docker as docker_sdk  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "docker package not installed — run: pip install docker"
        ) from exc

    client = docker_sdk.from_env()
    os.makedirs(worktree_path, exist_ok=True)

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _stream_logs() -> None:
        container = None
        try:
            container = client.containers.run(
                image,
                command,
                volumes={worktree_path: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                environment=env,
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                network_mode=network_mode,
                detach=True,
                remove=False,
            )
            for chunk in container.logs(stream=True, follow=True):
                # Docker multiplexes stdout/stderr with an 8-byte header
                # Strip header if present (first byte is 1=stdout, 2=stderr)
                if len(chunk) > 8 and chunk[0] in (1, 2):
                    payload = chunk[8:]
                else:
                    payload = chunk
                text = payload.decode("utf-8", errors="replace")
                for line in text.splitlines():
                    if line:
                        loop.call_soon_threadsafe(queue.put_nowait, line)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, f"[docker] error: {e}")
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    # Run the blocking stream in a thread
    thread_future = loop.run_in_executor(None, _stream_logs)

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    await thread_future


def is_docker_available() -> bool:
    """Quick check — True if Docker daemon is reachable."""
    try:
        import docker as docker_sdk  # type: ignore
        client = docker_sdk.from_env(timeout=3)
        client.ping()
        return True
    except Exception:
        return False


def image_exists(image: str = DOCKER_IMAGE) -> bool:
    """True if the named image is available locally."""
    try:
        import docker as docker_sdk  # type: ignore
        client = docker_sdk.from_env(timeout=3)
        client.images.get(image)
        return True
    except Exception:
        return False
