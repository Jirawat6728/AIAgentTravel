"""
Mock Data Script
สร้าง mock ข้อมูลลง database สำหรับ user_id ที่ระบุ
รวมถึง sessions, bookings (pending_payment), และ conversations

Usage:
    python -m scripts.mock_data <user_id> [num_sessions]
    
Example:
    python -m scripts.mock_data user_1234567890 3
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Load environment variables
_BASE_DIR = Path(__file__).parent.parent
_DOTENV_PATH = Path(os.getenv("DOTENV_PATH") or (_BASE_DIR / ".env"))
from dotenv import load_dotenv
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

from app.storage.connection_manager import MongoConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_mock_sessions(user_id: str, db, count: int = 3):
    """สร้าง mock sessions"""
    sessions_collection = db["sessions"]
    sessions = []
    
    destinations = [
        {"origin": "กรุงเทพ", "destination": "โตเกียว", "title": "ทริปโตเกียว 5 วัน 4 คืน"},
        {"origin": "กรุงเทพ", "destination": "โซล", "title": "ทริปโซล 4 วัน 3 คืน"},
        {"origin": "กรุงเทพ", "destination": "สิงคโปร์", "title": "ทริปสิงคโปร์ 3 วัน 2 คืน"},
    ]
    
    for i in range(count):
        dest = destinations[i % len(destinations)]
        trip_id = f"trip_{user_id}_{i+1}"
        chat_id = f"chat_{user_id}_{i+1}"
        session_id = f"{user_id}::{chat_id}"
        
        # สร้าง trip_plan แบบ mock
        trip_plan = {
            "travel": {
                "flights": {
                    "outbound": [
                        {
                            "status": "confirmed",
                            "requirements": {
                                "origin": dest["origin"],
                                "destination": dest["destination"],
                                "departure_date": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
                                "adults": 2,
                                "children": 0
                            },
                            "options_pool": [
                                {
                                    "id": f"flight_out_{i}",
                                    "title": f"เที่ยวบิน {dest['origin']} → {dest['destination']}",
                                    "price_amount": 15000 + (i * 2000),
                                    "currency": "THB",
                                    "category": "flight"
                                }
                            ],
                            "selected_option": {
                                "id": f"flight_out_{i}",
                                "title": f"เที่ยวบิน {dest['origin']} → {dest['destination']}",
                                "price_amount": 15000 + (i * 2000),
                                "currency": "THB"
                            }
                        }
                    ],
                    "inbound": [
                        {
                            "status": "confirmed",
                            "requirements": {
                                "origin": dest["destination"],
                                "destination": dest["origin"],
                                "departure_date": (datetime.utcnow() + timedelta(days=35)).strftime("%Y-%m-%d"),
                                "adults": 2,
                                "children": 0
                            },
                            "options_pool": [
                                {
                                    "id": f"flight_in_{i}",
                                    "title": f"เที่ยวบิน {dest['destination']} → {dest['origin']}",
                                    "price_amount": 15000 + (i * 2000),
                                    "currency": "THB",
                                    "category": "flight"
                                }
                            ],
                            "selected_option": {
                                "id": f"flight_in_{i}",
                                "title": f"เที่ยวบิน {dest['destination']} → {dest['origin']}",
                                "price_amount": 15000 + (i * 2000),
                                "currency": "THB"
                            }
                        }
                    ]
                }
            },
            "accommodation": {
                "segments": [
                    {
                        "status": "confirmed",
                        "requirements": {
                            "location": dest["destination"],
                            "check_in": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
                            "check_out": (datetime.utcnow() + timedelta(days=34)).strftime("%Y-%m-%d"),
                            "guests": 2
                        },
                        "options_pool": [
                            {
                                "id": f"hotel_{i}",
                                "title": f"โรงแรมใน{dest['destination']}",
                                "price_amount": 8000 + (i * 1000),
                                "currency": "THB",
                                "category": "hotel"
                            }
                        ],
                        "selected_option": {
                            "id": f"hotel_{i}",
                            "title": f"โรงแรมใน{dest['destination']}",
                            "price_amount": 8000 + (i * 1000),
                            "currency": "THB"
                        }
                    }
                ]
            }
        }
        
        session_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "trip_id": trip_id,
            "chat_id": chat_id,
            "trip_plan": trip_plan,
            "title": dest["title"],
            "created_at": (datetime.utcnow() - timedelta(days=count-i)).isoformat(),
            "last_updated": (datetime.utcnow() - timedelta(hours=count-i)).isoformat(),
            "metadata": {}
        }
        
        try:
            result = await sessions_collection.insert_one(session_doc)
            logger.info(f"✅ Created session: {session_id} (trip_id: {trip_id})")
            sessions.append(session_doc)
        except Exception as e:
            logger.error(f"❌ Failed to create session {session_id}: {e}")
    
    return sessions


async def create_mock_bookings(user_id: str, db, sessions: list):
    """สร้าง mock bookings (pending_payment)"""
    bookings_collection = db["bookings"]
    bookings = []
    
    for i, session in enumerate(sessions):
        trip_plan = session.get("trip_plan", {})
        
        # คำนวณราคารวม
        total_price = 0
        flights = trip_plan.get("travel", {}).get("flights", {})
        outbound = flights.get("outbound", [])
        inbound = flights.get("inbound", [])
        hotels = trip_plan.get("accommodation", {}).get("segments", [])
        
        if outbound and outbound[0].get("selected_option"):
            total_price += outbound[0]["selected_option"].get("price_amount", 0)
        if inbound and inbound[0].get("selected_option"):
            total_price += inbound[0]["selected_option"].get("price_amount", 0)
        if hotels and hotels[0].get("selected_option"):
            total_price += hotels[0]["selected_option"].get("price_amount", 0)
        
        # สร้าง travel_slots
        travel_slots = {
            "origin_city": outbound[0].get("requirements", {}).get("origin", "") if outbound else "",
            "destination_city": outbound[0].get("requirements", {}).get("destination", "") if outbound else "",
            "departure_date": outbound[0].get("requirements", {}).get("departure_date", "") if outbound else "",
            "return_date": inbound[0].get("requirements", {}).get("departure_date", "") if inbound else "",
            "adults": outbound[0].get("requirements", {}).get("adults", 2) if outbound else 2,
            "children": outbound[0].get("requirements", {}).get("children", 0) if outbound else 0,
            "nights": 4 if i == 0 else (3 if i == 1 else 2),
            "flights": [
                {
                    "requirements": outbound[0].get("requirements", {}) if outbound else {},
                    "selected_option": outbound[0].get("selected_option", {}) if outbound else {}
                },
                {
                    "requirements": inbound[0].get("requirements", {}) if inbound else {},
                    "selected_option": inbound[0].get("selected_option", {}) if inbound else {}
                }
            ] if outbound and inbound else [],
            "accommodations": [
                {
                    "requirements": hotels[0].get("requirements", {}) if hotels else {},
                    "selected_option": hotels[0].get("selected_option", {}) if hotels else {}
                }
            ] if hotels else []
        }
        
        booking_doc = {
            "trip_id": session.get("trip_id"),
            "chat_id": session.get("chat_id"),
            "user_id": user_id,
            "session_id": session.get("session_id"),
            "plan": trip_plan,
            "travel_slots": travel_slots,
            "total_price": total_price,
            "currency": "THB",
            "status": "pending_payment",  # ✅ ยังไม่จ่ายเงิน
            "created_at": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "metadata": {
                "mode": "normal",
                "auto_booked": False
            }
        }

        try:
            result = await bookings_collection.insert_one(booking_doc)
            booking_id = str(result.inserted_id)
            logger.info(f"✅ Created booking: {booking_id} (status: pending_payment, price: {total_price} THB)")
            bookings.append(booking_doc)
        except Exception as e:
            logger.error(f"❌ Failed to create booking for session {session.get('session_id')}: {e}")
    
    return bookings


async def create_mock_conversations(user_id: str, db, sessions: list):
    """สร้าง mock conversations"""
    conversations_collection = db["conversations"]
    
    for session in sessions:
        conversation_doc = {
            "session_id": session.get("session_id"),
            "user_id": user_id,
            "messages": [
                {
                    "role": "user",
                    "content": f"ฉันต้องการไป{session.get('title', '')}",
                    "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "metadata": {}
                },
                {
                    "role": "assistant",
                    "content": f"เข้าใจแล้วค่ะ ฉันจะช่วยคุณวางแผนทริป{session.get('title', '')}",
                    "timestamp": (datetime.utcnow() - timedelta(days=1, hours=23)).isoformat(),
                    "metadata": {}
                }
            ],
            "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        
        try:
            await conversations_collection.insert_one(conversation_doc)
            logger.info(f"✅ Created conversation for session: {session.get('session_id')}")
        except Exception as e:
            logger.error(f"❌ Failed to create conversation for session {session.get('session_id')}: {e}")


async def mock_data_for_user(user_id: str, num_sessions: int = 3):
    """
    สร้าง mock ข้อมูลสำหรับ user_id ที่ระบุ
    
    Args:
        user_id: User ID ที่ต้องการสร้างข้อมูล
        num_sessions: จำนวน sessions ที่ต้องการสร้าง (default: 3)
    """
    try:
        # เชื่อมต่อ MongoDB
        mongo_manager = MongoConnectionManager.get_instance()
        await mongo_manager.connect()
        db = mongo_manager.get_mongo_database()
        
        logger.info(f"🚀 Starting mock data creation for user_id: {user_id}")
        logger.info(f"📊 Will create {num_sessions} sessions, bookings, and conversations")
        
        # 1. สร้าง Sessions
        logger.info("📝 Creating mock sessions...")
        sessions = await create_mock_sessions(user_id, db, num_sessions)
        logger.info(f"✅ Created {len(sessions)} sessions")
        
        # 2. สร้าง Bookings (pending_payment)
        logger.info("📦 Creating mock bookings (pending_payment)...")
        bookings = await create_mock_bookings(user_id, db, sessions)
        logger.info(f"✅ Created {len(bookings)} bookings with status: pending_payment")
        
        # 3. สร้าง Conversations
        logger.info("💬 Creating mock conversations...")
        await create_mock_conversations(user_id, db, sessions)
        logger.info(f"✅ Created {len(sessions)} conversations")
        
        logger.info("="*60)
        logger.info(f"✅ Mock data creation completed for user_id: {user_id}")
        logger.info(f"   - Sessions: {len(sessions)}")
        logger.info(f"   - Bookings: {len(bookings)} (all pending_payment)")
        logger.info(f"   - Conversations: {len(sessions)}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Failed to create mock data: {e}", exc_info=True)
        raise
    finally:
        # ไม่ต้อง disconnect เพราะใช้ connection manager
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mock_data.py <user_id> [num_sessions]")
        print("Example: python mock_data.py user_1234567890 3")
        sys.exit(1)
    
    user_id = sys.argv[1]
    num_sessions = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    asyncio.run(mock_data_for_user(user_id, num_sessions))
