import time
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()

_start_time: float = time.time()


@router.get("/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime": time.time() - _start_time,
        },
    }
