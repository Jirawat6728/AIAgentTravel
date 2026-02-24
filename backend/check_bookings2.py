import sys, asyncio, json
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(".env", override=True)

async def check():
    from app.storage.mongodb_storage import MongoStorage
    s = MongoStorage()
    await s.connect()
    db = s.db
    
    bookings = await db["bookings"].find({}).to_list(10)
    for b in bookings:
        print("booking_id:", b.get("booking_id"))
        print("  user_id:", b.get("user_id"))
        print("  status:", b.get("status"))
        print("  session_id:", b.get("session_id"))
        print("  created_at:", b.get("created_at"))
        plan = b.get("trip_plan", {})
        print("  plan keys:", list(plan.keys())[:5])
        print()

asyncio.run(check())
