"""
Simple MongoDB Connection Test
Tests basic MongoDB connectivity without full app dependencies
"""

import asyncio
import sys
import os
from pathlib import Path

# Try to import motor
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    print("[OK] motor library imported successfully")
except ImportError:
    print("[ERROR] motor library not found. Please install: pip install motor")
    sys.exit(1)

# Get MongoDB connection string from env or use default
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "travel_agent")

print("=" * 50)
print("MongoDB Connection Test")
print("=" * 50)
print(f"\nConnection String: {MONGODB_URI}")
print(f"Database Name: {MONGODB_DATABASE}")


async def test_connection():
    """Test basic MongoDB connection"""
    client = None
    
    try:
        # Create client
        print("\n[1/4] Creating MongoDB client...")
        client = AsyncIOMotorClient(MONGODB_URI)
        print("[OK] Client created")
        
        # Test ping
        print("\n[2/4] Testing ping...")
        result = await client.admin.command('ping')
        print(f"[OK] Ping successful: {result}")
        
        # List databases
        print("\n[3/4] Listing databases...")
        db_names = await client.list_database_names()
        print(f"[OK] Available databases: {db_names}")
        
        # Test database access
        print("\n[4/4] Testing database access...")
        db = client[MONGODB_DATABASE]
        collections = await db.list_collection_names()
        print(f"[OK] Collections in '{MONGODB_DATABASE}': {collections}")
        
        # Test write (create a test document)
        print("\n[5/5] Testing write operation...")
        test_collection = db["test_connection"]
        await test_collection.insert_one({
            "test": True,
            "message": "Connection test successful"
        })
        print("[OK] Write operation successful")
        
        # Test read
        doc = await test_collection.find_one({"test": True})
        print(f"[OK] Read operation successful: {doc}")
        
        # Cleanup
        await test_collection.delete_one({"test": True})
        print("[OK] Cleanup completed")
        
        print("\n" + "=" * 50)
        print("[OK] All tests passed! MongoDB connection is working.")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running")
        print("2. Check MONGODB_URI in .env file")
        print("3. Verify network connectivity")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if client:
            client.close()
            print("\n[OK] Connection closed")


if __name__ == "__main__":
    print("\nStarting test...\n")
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

