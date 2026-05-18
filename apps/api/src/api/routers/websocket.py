import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..database import get_db
from ..services import execution_service
from ..bus import event_bus

router = APIRouter(tags=["websocket"])

TERMINAL_STATUSES = {"completed", "failed", "stopped"}


@router.websocket("/ws/executions/{execution_id}")
async def execution_stream(websocket: WebSocket, execution_id: str):
    await websocket.accept()

    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            await websocket.close(code=4004)
            return

        # 1. Replay persisted logs
        logs = await execution_service.get_logs(db, execution_id)

    async def safe_send(payload: dict) -> bool:
        """Send a JSON frame; return False if client already disconnected."""
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    for log in logs:
        if not await safe_send({
            "type": "log",
            "sequence": log.sequence,
            "level": log.level,
            "content": log.content,
            "timestamp": log.timestamp,
        }):
            return

    # Send current status
    if not await safe_send({"type": "status", "status": execution.status, "pid": execution.pid}):
        return

    # If already terminal, send done and close
    if execution.status in TERMINAL_STATUSES:
        await safe_send({
            "type": "done",
            "status": execution.status,
            "exit_code": execution.exit_code,
            "token_usage": execution.token_usage,
            "error_message": execution.error_message,
        })
        try:
            await websocket.close()
        except Exception:
            pass
        return

    # 2. Subscribe to live events
    queue = event_bus.subscribe(execution_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                if not await safe_send({"type": "ping"}):
                    break
                continue

            if event.get("type") == "__done__":
                async with get_db() as db:
                    execution = await execution_service.get(db, execution_id)
                await safe_send({
                    "type": "done",
                    "status": execution.status if execution else "unknown",
                    "exit_code": execution.exit_code if execution else None,
                    "token_usage": execution.token_usage if execution else None,
                    "error_message": execution.error_message if execution else None,
                })
                break

            if not await safe_send(event):
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(execution_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
