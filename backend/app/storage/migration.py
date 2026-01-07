"""
Migration Script: JSON Storage to MongoDB
Utility to migrate existing JSON sessions to MongoDB
"""

import asyncio
from pathlib import Path
from app.storage.json_storage import JsonFileStorage
from app.storage.mongodb_storage import MongoStorage
from app.core.logging import get_logger

logger = get_logger(__name__)


async def migrate_json_to_mongodb(
    json_sessions_dir: Path,
    mongodb_uri: str = "mongodb://localhost:27017",
    mongodb_database: str = "travel_agent"
):
    """
    Migrate all JSON session files to MongoDB
    
    Args:
        json_sessions_dir: Directory containing JSON session files
        mongodb_uri: MongoDB connection string
        mongodb_database: MongoDB database name
    """
    json_storage = JsonFileStorage(sessions_dir=json_sessions_dir)
    mongo_storage = MongoStorage(
        connection_string=mongodb_uri,
        database_name=mongodb_database
    )
    
    await mongo_storage.connect()
    
    try:
        # Get all JSON session files
        session_files = list(json_sessions_dir.glob("*.json"))
        total = len(session_files)
        
        logger.info(f"Starting migration: {total} sessions to migrate")
        
        migrated = 0
        failed = 0
        
        for session_file in session_files:
            try:
                # Extract session_id from filename
                # Format: session_{session_id}.json or {session_id}.json
                filename = session_file.stem
                if filename.startswith("session_"):
                    session_id = filename.replace("session_", "").replace("_", "::")
                else:
                    session_id = filename.replace("_", "::")
                
                # Load session from JSON
                session = await json_storage.get_session(session_id)
                
                # Save to MongoDB
                await mongo_storage.save_session(session)
                
                migrated += 1
                if migrated % 10 == 0:
                    logger.info(f"Migrated {migrated}/{total} sessions...")
            
            except Exception as e:
                logger.error(f"Failed to migrate {session_file.name}: {e}", exc_info=True)
                failed += 1
        
        logger.info(f"Migration completed: {migrated} migrated, {failed} failed")
        
    finally:
        await mongo_storage.disconnect()


if __name__ == "__main__":
    import sys
    json_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data/sessions")
    asyncio.run(migrate_json_to_mongodb(json_dir))

