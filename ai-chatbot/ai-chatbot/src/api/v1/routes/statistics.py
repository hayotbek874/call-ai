import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.logging import get_logger
from src.core.security import decode_access_token
from src.services.statistics_service import StatisticsService

logger = get_logger(__name__)

router = APIRouter(tags=["statistics"])

STATS_INTERVAL = 2

@router.websocket("/ws/stats")
async def ws_stats(ws: WebSocket) -> None:
    token = ws.query_params.get("token")
    if not token or decode_access_token(token) is None:
        await ws.close(code=4001, reason="unauthorized")
        return

    await ws.accept()
    engine = ws.app.state.engine
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    try:
        while True:
            async with factory() as session:
                svc = StatisticsService(session)
                data = await svc.collect()
            await ws.send_text(json.dumps(data, ensure_ascii=False))
            await asyncio.sleep(STATS_INTERVAL)
    except WebSocketDisconnect:
        await logger.info("ws_stats_disconnected")
    except Exception:
        await logger.exception("ws_stats_error")
        await ws.close(code=1011)
