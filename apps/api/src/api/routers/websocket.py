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

    for log in logs:
        await websocket.send_json({
            "type": "log",
            "sequence": log.sequence,
            "level": log.level,
            "content": log.content,
            "timestamp": log.timestamp,
        })

    # Send current status
    await websocket.send_json({
        "type": "status",
        "status": execution.status,
        "pid": execution.pid,
    })

    # If already terminal, send done and close
    if execution.status in TERMINAL_STATUSES:
        await websocket.send_json({
            "type": "done",
            "status": execution.status,
            "exit_code": execution.exit_code,
            "token_usage": execution.token_usage,
        })
        await websocket.close()
        return

    # 2. Subscribe to live events
    queue = event_bus.subscribe(execution_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            if event.get("type") == "__done__":
                async with get_db() as db:
                    execution = await execution_service.get(db, execution_id)
                await websocket.send_json({
                    "type": "done",
                    "status": execution.status if execution else "unknown",
                    "exit_code": execution.exit_code if execution else None,
                    "token_usage": execution.token_usage if execution else None,
                })
                break

            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(execution_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
