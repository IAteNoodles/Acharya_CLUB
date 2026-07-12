from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, require_teacher_or_admin
from app.core.database import get_db
from app.schemas.common import SuccessResponse
from app.services.reports import ReportService

router = APIRouter(tags=["reports"])


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    stats = await ReportService.get_dashboard_stats(db)
    return SuccessResponse(data=stats)
