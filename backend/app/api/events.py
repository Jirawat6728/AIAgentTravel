from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.services.events_service import get_events_from_google


logger = get_logger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/search")
async def search_events(
    location: str = Query(..., description="ชื่อเมือง/จังหวัด/สถานที่ปลายทางที่ต้องการค้นหาอีเวนต์"),
):
    """
    ค้นหาอีเวนต์/กิจกรรมจาก Google Places รอบๆ location ที่ระบุ
    ใช้โดยทั้ง Agent Mode และ frontend (เช่น หน้า Explore หรือ Planner)
    """
    try:
        events = await get_events_from_google(location)
        return {"ok": True, "events": events}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"/api/events/search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events from Google Places")

