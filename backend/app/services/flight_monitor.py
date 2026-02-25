"""
Proactive Crisis Manager — FlightMonitorService
Polls active bookings for flight delays/cancellations and pushes SSE notifications.
Runs as a periodic background task (every 30 min on local dev).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.storage.connection_manager import get_db

logger = get_logger(__name__)

# Minimum delay threshold (minutes) before sending an alert
DELAY_THRESHOLD_MINUTES = 30
# How long after departure we stop monitoring (hours)
MONITOR_WINDOW_HOURS = 24


class FlightMonitorService:
    """Checks all active bookings for flight status changes and notifies users."""

    def __init__(self, db=None):
        self._db = db  # injected for testability; lazy-loads from connection_manager otherwise

    @property
    def db(self):
        if self._db is not None:
            return self._db
        return get_db()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def check_all_active_bookings(self) -> None:
        """Main loop entry — scans every active booking with flight segments."""
        try:
            db = self.db
            if db is None:
                logger.warning("[FlightMonitor] No DB connection available, skipping check.")
                return

            bookings_col = db["bookings"]
            # Find active bookings that have flight order data and haven't been cancelled
            cursor = bookings_col.find(
                {
                    "status": {"$in": ["confirmed", "pending", "active"]},
                    "flight_order_id": {"$exists": True, "$ne": None},
                },
                {"booking_id": 1, "user_id": 1, "flight_order_id": 1,
                 "flight_status": 1, "departure_date": 1, "segments": 1},
            )

            checked = 0
            async for booking in cursor:
                booking_id = booking.get("booking_id") or str(booking.get("_id", ""))
                user_id = booking.get("user_id", "")
                if not booking_id or not user_id:
                    continue
                try:
                    await self.check_booking(booking_id, user_id, booking)
                    checked += 1
                except Exception as e:
                    logger.warning(f"[FlightMonitor] Error checking booking {booking_id}: {e}")

            logger.info(f"[FlightMonitor] Checked {checked} active bookings.")
        except Exception as e:
            logger.error(f"[FlightMonitor] check_all_active_bookings failed: {e}", exc_info=True)

    async def check_booking(
        self,
        booking_id: str,
        user_id: str,
        booking_doc: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Check a single booking for flight status changes."""
        db = self.db
        if db is None:
            return

        if booking_doc is None:
            booking_doc = await db["bookings"].find_one({"booking_id": booking_id})
        if not booking_doc:
            return

        flight_order_id = booking_doc.get("flight_order_id")
        if not flight_order_id:
            return

        # Try Amadeus flight schedule API
        delay_minutes = await self._fetch_delay_minutes(flight_order_id, booking_doc)
        if delay_minutes is None:
            return  # API unavailable or no data

        current_status = booking_doc.get("flight_status", "on_time")

        if delay_minutes >= DELAY_THRESHOLD_MINUTES:
            new_status = "delayed"
            if current_status != "delayed":
                await self._update_booking_flight_status(db, booking_id, new_status, delay_minutes)
                await self._send_delay_notification(user_id, booking_doc, delay_minutes)
        elif delay_minutes < 0:
            # Negative delay = cancelled / diverted
            new_status = "cancelled"
            if current_status != "cancelled":
                await self._update_booking_flight_status(db, booking_id, new_status, 0)
                await self._send_cancellation_notification(user_id, booking_doc)
        else:
            # Back on time after being delayed
            if current_status == "delayed":
                await self._update_booking_flight_status(db, booking_id, "on_time", 0)
                await self._send_on_time_notification(user_id, booking_doc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_delay_minutes(
        self, flight_order_id: str, booking_doc: Dict[str, Any]
    ) -> Optional[int]:
        """
        Calls Amadeus /v2/schedule/flights to check real-time status.
        Returns delay in minutes (negative = cancelled), or None if unavailable.
        This is a best-effort call — failures are silently swallowed.
        """
        try:
            from app.services.travel_service import TravelService

            travel_svc = TravelService()

            # Extract flight number + date from booking segments
            segments = booking_doc.get("segments") or []
            if not segments:
                return None

            first_seg = segments[0] if isinstance(segments, list) else {}
            carrier_code = first_seg.get("carrier_code") or first_seg.get("airline_code", "")
            flight_number = first_seg.get("flight_number", "")
            departure_date = first_seg.get("departure_date") or booking_doc.get("departure_date", "")

            if not (carrier_code and flight_number and departure_date):
                return None

            flight_num_only = "".join(filter(str.isdigit, flight_number))
            result = await travel_svc.get_flight_schedule(
                carrier_code=carrier_code,
                flight_number=flight_num_only,
                scheduled_departure_date=departure_date,
            )
            if not result:
                return None

            # Parse delay from result
            delay = result.get("delay_minutes") or result.get("delayMinutes")
            if delay is not None:
                return int(delay)

            # Infer from status string
            status_str = (result.get("status") or "").lower()
            if "cancel" in status_str:
                return -1
            return 0
        except Exception as e:
            logger.debug(f"[FlightMonitor] _fetch_delay_minutes error: {e}")
            return None

    async def _update_booking_flight_status(
        self, db, booking_id: str, status: str, delay_minutes: int
    ) -> None:
        try:
            await db["bookings"].update_one(
                {"booking_id": booking_id},
                {
                    "$set": {
                        "flight_status": status,
                        "delay_minutes": delay_minutes,
                        "flight_status_updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        except Exception as e:
            logger.warning(f"[FlightMonitor] Failed to update flight_status for {booking_id}: {e}")

    async def _send_delay_notification(
        self, user_id: str, booking_doc: Dict[str, Any], delay_minutes: int
    ) -> None:
        try:
            from app.services.notification_service import create_and_push_notification

            route = self._format_route(booking_doc)
            hours, mins = divmod(delay_minutes, 60)
            delay_str = f"{hours} ชม. {mins} นาที" if hours else f"{mins} นาที"

            await create_and_push_notification(
                db=self.db,
                user_id=user_id,
                notif_type="flight_delay",
                title=f"✈️ เที่ยวบินล่าช้า {delay_str}",
                message=(
                    f"เที่ยวบิน{route}ล่าช้าประมาณ {delay_str} "
                    f"จากกำหนดการเดิม นายหน้าของคุณกำลังติดตามสถานการณ์อยู่"
                ),
                booking_id=booking_doc.get("booking_id"),
                metadata={"delay_minutes": delay_minutes, "route": route},
            )
        except Exception as e:
            logger.warning(f"[FlightMonitor] Failed to send delay notification: {e}")

    async def _send_cancellation_notification(
        self, user_id: str, booking_doc: Dict[str, Any]
    ) -> None:
        try:
            from app.services.notification_service import create_and_push_notification

            route = self._format_route(booking_doc)
            await create_and_push_notification(
                db=self.db,
                user_id=user_id,
                notif_type="flight_cancelled",
                title="⚠️ เที่ยวบินถูกยกเลิก",
                message=(
                    f"เที่ยวบิน{route}ถูกยกเลิกแล้ว "
                    f"กรุณาติดต่อนายหน้าของคุณเพื่อจัดการทางเลือกอื่น"
                ),
                booking_id=booking_doc.get("booking_id"),
                metadata={"route": route},
            )
        except Exception as e:
            logger.warning(f"[FlightMonitor] Failed to send cancellation notification: {e}")

    async def _send_on_time_notification(
        self, user_id: str, booking_doc: Dict[str, Any]
    ) -> None:
        try:
            from app.services.notification_service import create_and_push_notification

            route = self._format_route(booking_doc)
            await create_and_push_notification(
                db=self.db,
                user_id=user_id,
                notif_type="flight_on_time",
                title="✅ เที่ยวบินกลับมาตรงเวลา",
                message=f"เที่ยวบิน{route}กลับมาตรงเวลาตามกำหนดการเดิมแล้ว",
                booking_id=booking_doc.get("booking_id"),
                metadata={"route": route},
            )
        except Exception as e:
            logger.warning(f"[FlightMonitor] Failed to send on-time notification: {e}")

    @staticmethod
    def _format_route(booking_doc: Dict[str, Any]) -> str:
        """Extract a human-readable route from booking_doc."""
        try:
            segs = booking_doc.get("segments") or []
            if segs and isinstance(segs, list):
                origin = segs[0].get("origin") or segs[0].get("departure_iata", "")
                dest = segs[-1].get("destination") or segs[-1].get("arrival_iata", "")
                if origin and dest:
                    return f" {origin}→{dest} "
        except Exception:
            pass
        return " "
