"""
Test MongoDB Connection
Simple script to test database connectivity
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.storage.mongodb_storage import MongoStorage
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging("test_db", "INFO")


async def test_connection():
    """Test MongoDB connection"""
    print("=" * 50)
    print("Testing MongoDB Connection")
    print("=" * 50)
    
    # Get connection info
    print(f"\nConnection String: {settings.mongodb_uri}")
    print(f"Database Name: {settings.mongodb_database}")
    
    # Create storage instance
    storage = MongoStorage()
    
    try:
        # Test connection
        print("\n[1/5] Connecting to MongoDB...")
        await storage.connect()
        print("[OK] Connection successful!")
        
        # Test ping
        print("\n[2/5] Testing ping...")
        ping_result = await storage.client.admin.command('ping')
        print(f"[OK] Ping successful: {ping_result}")
        
        # Test database access
        print("\n[3/5] Testing database access...")
        db_names = await storage.client.list_database_names()
        print(f"[OK] Available databases: {db_names}")
        
        # Test collection access
        print("\n[4/5] Testing collection access...")
        collections = await storage.db.list_collection_names()
        print(f"[OK] Collections in '{settings.mongodb_database}': {collections}")
        
        # Test create/get session
        print("\n[5/5] Testing session operations...")
        test_session_id = "test_user::test_conv"
        session = await storage.get_session(test_session_id)
        print(f"[OK] Session created/retrieved: {session.session_id}")
        print(f"  - User ID: {session.user_id}")
        print(f"  - Trip Plan: {len(session.trip_plan.flights)} flights")
        
        # Test save session
        session.title = "Test Session"
        await storage.save_session(session)
        print("[OK] Session saved successfully")
        
        # Test update title
        await storage.update_title(test_session_id, "Updated Test Title")
        print("[OK] Title updated successfully")
        
        # Verify
        saved_session = await storage.get_session(test_session_id)
        print(f"[OK] Verified: Title = '{saved_session.title}'")
        
        print("\n" + "=" * 50)
        print("[OK] All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Disconnect
        await storage.disconnect()
        print("\n[OK] Disconnected from MongoDB")
    
    return True


async def test_indexes():
    """Test if indexes are created correctly"""
    print("\n" + "=" * 50)
    print("Testing Indexes")
    print("=" * 50)
    
    storage = MongoStorage()
    
    try:
        await storage.connect()
        
        # Get indexes
        indexes = await storage.sessions_collection.list_indexes().to_list(length=100)
        
        print(f"\nIndexes in 'sessions' collection:")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        
        print("\n[OK] Index check completed")
        
    except Exception as e:
        print(f"\n[ERROR] Error checking indexes: {e}")
    finally:
        await storage.disconnect()


if __name__ == "__main__":
    print("\nStarting MongoDB Connection Test...\n")
    
    # Run connection test
    success = asyncio.run(test_connection())
    
    if success:
        # Run index test
        asyncio.run(test_indexes())
    
    sys.exit(0 if success else 1)

