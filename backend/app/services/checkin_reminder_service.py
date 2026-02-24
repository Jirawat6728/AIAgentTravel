"""
Check-in Reminder & Flight Alert Service
- แจ้งเตือนเช็คอินเครื่องบิน 24 ชม. และ 2 ชม. ก่อนออกเดินทาง
- แจ้งเตือนเช็คอินโรงแรมวันที่เข้าพัก
- แจ้งเตือน flight delay / flight cancelled (จาก booking metadata)
- แจ้งเตือนทริปเปลี่ยนแปลงมากเกินไป (trip alert)
รัน background task ทุก 15 นาที
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

# ระยะเวลาก่อนเช็คอินที่จะส่งแจ้งเตือน
FLIGHT_CHECKIN_WINDOWS_HOURS = [24, 2]   # แจ้ง 24h และ 2h ก่อน departure
HOTEL_CHECKIN_WINDOW_HOURS = 8            # แจ้งเช้าวันที่เช็คอิน (8h ก่อน noon)
REMINDER_COOLDOWN_HOURS = 1              # ไม่ส่งซ้ำถ้าส่งไปแล้วภายใน 1 ชม.


def _parse_dt(value: Any) -> Optional[datetime]:
    """แปลง string/datetime เป็น datetime object"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        from dateutil import parser as dp
        return dp.parse(str(value))
    except Exception:
        return None


def _already_sent(sent_reminders: list, key: str) -> bool:
    """ตรวจว่าเคยส่ง reminder key นี้ไปแล้วหรือยัง"""
    return key in (sent_reminders or [])


async def process_checkin_reminders(db) -> int:
    """
    ตรวจ bookings ทั้งหมดที่ status=paid/confirmed แล้วส่ง check-in reminders
    คืนจำนวน notifications ที่ส่ง
    """
    from app.services.notification_service import create_and_push_notification

    sent_count = 0
    now = datetime.utcnow()

    try:
        bookings_col = db.get_collection("bookings")
        cursor = bookings_col.find(
            {"status": {"$in": ["paid", "confirmed"]}},
            {"user_id": 1, "booking_id": 1, "plan": 1, "sent_reminders": 1, "_id": 1}
        )
        bookings: List[Dict] = await cursor.to_list(length=500)
    except Exception as e:
        logger.error(f"[CheckinReminder] Failed to fetch bookings: {e}")
        return 0

    for booking in bookings:
        user_id = booking.get("user_id")
        booking_id = str(booking.get("booking_id") or booking.get("_id", ""))
        plan = booking.get("plan") or {}
        sent_reminders = booking.get("sent_reminders") or []
        new_reminders = []

        # ── Flight check-in reminders ──────────────────────────────────────
        travel = plan.get("travel") or {}
        flights = travel.get("flights") or {}
        for direction in ("outbound", "inbound"):
            segments = flights.get(direction) or []
            for idx, seg in enumerate(segments):
                opt = seg.get("selected_option") or {}
                dep_str = (
                    opt.get("departure_time")
                    or opt.get("departure")
                    or (opt.get("raw_data") or {}).get("itineraries", [{}])[0]
                       .get("segments", [{}])[0].get("departure", {}).get("at")
                )
                dep_dt = _parse_dt(dep_str)
                if not dep_dt:
                    continue

                for hours in FLIGHT_CHECKIN_WINDOWS_HOURS:
                    reminder_key = f"flight_{direction}_{idx}_{hours}h"
                    if _already_sent(sent_reminders, reminder_key):
                        continue
                    trigger_time = dep_dt - timedelta(hours=hours)
                    if trigger_time <= now < trigger_time + timedelta(hours=REMINDER_COOLDOWN_HOURS):
                        flight_no = (
                            opt.get("flight_number")
                            or (opt.get("raw_data") or {}).get("itineraries", [{}])[0]
                               .get("segments", [{}])[0].get("carrierCode", "")
                        )
                        label = "24 ชั่วโมง" if hours == 24 else f"{hours} ชั่วโมง"
                        await create_and_push_notification(
                            db=db,
                            user_id=user_id,
                            notif_type="checkin_reminder_flight",
                            title=f"เตือนเช็คอินเครื่องบิน ({label})",
                            message=(
                                f"เที่ยวบิน {flight_no or direction} ออกเดินทางใน {label} "
                                f"({dep_dt.strftime('%d/%m %H:%M')} UTC) "
                                f"อย่าลืมเช็คอินออนไลน์!"
                            ),
                            booking_id=booking_id,
                            metadata={"direction": direction, "hours_before": hours, "departure": dep_str},
                        )
                        new_reminders.append(reminder_key)
                        sent_count += 1

        # ── Hotel check-in reminder ────────────────────────────────────────
        acc = plan.get("accommodation") or {}
        acc_segments = acc.get("segments") if isinstance(acc, dict) else (plan.get("accommodations") or [])
        if not isinstance(acc_segments, list):
            acc_segments = []

        for idx, seg in enumerate(acc_segments):
            checkin_str = (
                (seg.get("selected_option") or {}).get("check_in")
                or seg.get("check_in")
                or seg.get("checkIn")
            )
            checkin_dt = _parse_dt(checkin_str)
            if not checkin_dt:
                continue

            reminder_key = f"hotel_{idx}_checkin"
            if _already_sent(sent_reminders, reminder_key):
                continue

            # แจ้งเตือนตอนเช้า (8h ก่อน noon = 04:00 UTC ของวันเช็คอิน)
            trigger_time = checkin_dt.replace(hour=4, minute=0, second=0, microsecond=0)
            if trigger_time <= now < trigger_time + timedelta(hours=REMINDER_COOLDOWN_HOURS):
                hotel_name = (
                    (seg.get("selected_option") or {}).get("hotel_name")
                    or seg.get("hotel_name")
                    or "โรงแรม"
                )
                await create_and_push_notification(
                    db=db,
                    user_id=user_id,
                    notif_type="checkin_reminder_hotel",
                    title="เตือนเช็คอินโรงแรมวันนี้",
                    message=(
                        f"วันนี้คือวันเช็คอิน {hotel_name} "
                        f"({checkin_dt.strftime('%d/%m/%Y')}) "
                        f"เตรียมเอกสารและบัตรเครดิตให้พร้อม!"
                    ),
                    booking_id=booking_id,
                    metadata={"hotel_name": hotel_name, "check_in": checkin_str},
                )
                new_reminders.append(reminder_key)
                sent_count += 1

        # บันทึก sent_reminders กลับ DB
        if new_reminders:
            try:
                from bson import ObjectId
                filt = {"_id": ObjectId(str(booking["_id"]))}
                await bookings_col.update_one(
                    filt,
                    {"$addToSet": {"sent_reminders": {"$each": new_reminders}}}
                )
            except Exception as e:
                logger.warning(f"[CheckinReminder] Failed to update sent_reminders for {booking_id}: {e}")

    logger.info(f"[CheckinReminder] Processed {len(bookings)} bookings, sent {sent_count} reminders")
    return sent_count


async def check_trip_integrity(db) -> int:
    """
    ตรวจ bookings ที่มีการเปลี่ยนแปลงมากเกินไป (เช่น flight ถูก cancel โดยสายการบิน)
    แล้วส่ง trip_alert notification
    """
    from app.services.notification_service import create_and_push_notification

    sent_count = 0
    try:
        bookings_col = db.get_collection("bookings")
        # ดู bookings ที่มี flag airline_cancelled หรือ flight_status เปลี่ยน
        cursor = bookings_col.find(
            {
                "status": {"$in": ["paid", "confirmed"]},
                "$or": [
                    {"flight_status": {"$in": ["cancelled", "delayed", "rescheduled"]}},
                    {"airline_cancelled": True},
                ]
            }
        )
        bookings: List[Dict] = await cursor.to_list(length=200)
    except Exception as e:
        logger.error(f"[TripIntegrity] Failed to fetch bookings: {e}")
        return 0

    for booking in bookings:
        user_id = booking.get("user_id")
        booking_id = str(booking.get("booking_id") or booking.get("_id", ""))
        flight_status = booking.get("flight_status", "")
        sent_reminders = booking.get("sent_reminders") or []
        alert_key = f"trip_alert_{flight_status}"

        if _already_sent(sent_reminders, alert_key):
            continue

        if flight_status == "cancelled":
            title = "เที่ยวบินถูกยกเลิกโดยสายการบิน"
            msg = f"เที่ยวบินในการจอง #{booking_id[:8]} ถูกยกเลิกโดยสายการบิน กรุณาติดต่อสายการบินหรือแก้ไขทริปของคุณ"
            notif_type = "flight_cancelled"
        elif flight_status == "delayed":
            delay_min = booking.get("delay_minutes", 0)
            title = "เที่ยวบินล่าช้า"
            msg = f"เที่ยวบินในการจอง #{booking_id[:8]} ล่าช้าประมาณ {delay_min} นาที"
            notif_type = "flight_delayed"
        elif flight_status == "rescheduled":
            title = "เที่ยวบินเปลี่ยนเวลา"
            msg = f"เที่ยวบินในการจอง #{booking_id[:8]} มีการเปลี่ยนแปลงเวลา กรุณาตรวจสอบและแก้ไขทริปของคุณ"
            notif_type = "flight_rescheduled"
        else:
            continue

        await create_and_push_notification(
            db=db,
            user_id=user_id,
            notif_type=notif_type,
            title=title,
            message=msg,
            booking_id=booking_id,
            metadata={"flight_status": flight_status},
        )
        sent_count += 1

        try:
            from bson import ObjectId
            await bookings_col.update_one(
                {"_id": ObjectId(str(booking["_id"]))},
                {"$addToSet": {"sent_reminders": alert_key}}
            )
        except Exception:
            pass

    return sent_count


async def run_reminder_cycle(db) -> None:
    """รัน check-in reminders + trip integrity check ในรอบเดียว"""
    try:
        r1 = await process_checkin_reminders(db)
        r2 = await check_trip_integrity(db)
        if r1 + r2 > 0:
            logger.info(f"[ReminderCycle] Sent {r1} check-in + {r2} trip-alert notifications")
    except Exception as e:
        logger.error(f"[ReminderCycle] Error: {e}", exc_info=True)


async def start_reminder_scheduler(db, interval_minutes: int = 15) -> None:
    """Background loop — รัน reminder cycle ทุก interval_minutes นาที"""
    logger.info(f"[ReminderScheduler] Started (interval={interval_minutes}m)")
    while True:
        await asyncio.sleep(interval_minutes * 60)
        await run_reminder_cycle(db)
