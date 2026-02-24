import sys, asyncio
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(".env", override=True)

async def check():
    from app.storage.mongodb_storage import MongoStorage
    s = MongoStorage()
    await s.connect()
    db = s.db
    count = await db["bookings"].count_documents({})
    print("Total bookings:", count)
    user_bookings = await db["bookings"].find({"user_id": "user_1770680746"}).to_list(10)
    print("User bookings:", len(user_bookings))
    for b in user_bookings[:5]:
        print("  id:", b.get("booking_id"), "status:", b.get("status"))
    
    sessions = await db["sessions"].find({"user_id": "user_1770680746"}).sort("last_updated", -1).limit(5).to_list(5)
    for sess in sessions:
        plan = sess.get("trip_plan", {})
        wf = plan.get("workflow_step", "unknown")
        print("  session:", str(sess.get("session_id",""))[-15:], "step:", wf)

asyncio.run(check())
