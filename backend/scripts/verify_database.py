"""
Verify Database Collections and Indexes
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_database():
    """Verify all collections and indexes"""
    try:
        mongo_uri = settings.mongodb_uri
        database_name = settings.mongodb_database or "travel_agent"
        
        logger.info("=" * 80)
        logger.info("DATABASE VERIFICATION")
        logger.info("=" * 80)
        logger.info(f"Database: {database_name}")
        logger.info(f"MongoDB URI: {mongo_uri[:50]}...")
        logger.info("=" * 80)
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client[database_name]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("[OK] MongoDB connection successful\n")
        
        # Collections to verify
        collections = [
            "users",
            "sessions",
            "conversations",
            "memories",
            "bookings",
            "payments",
            "invoices",
            "refunds",
            "cost_tracking",
            "workflow_history",
            "api_logs",
            "error_logs",
            "audit_logs",
            "access_tokens",
            "security_events"
        ]
        
        logger.info(f"Verifying {len(collections)} collections...\n")
        
        total_indexes = 0
        total_documents = 0
        
        for collection_name in collections:
            try:
                collection = db[collection_name]
                
                # Get indexes
                indexes = await collection.list_indexes().to_list(length=100)
                index_count = len(indexes)
                total_indexes += index_count
                
                # Get document count
                doc_count = await collection.count_documents({})
                total_documents += doc_count
                
                logger.info(f"{collection_name:20s} | {index_count:2d} indexes | {doc_count:6d} documents")
                
            except Exception as e:
                logger.error(f"{collection_name:20s} | ERROR: {e}")
        
        logger.info("=" * 80)
        logger.info(f"SUMMARY:")
        logger.info(f"  Collections: {len(collections)}")
        logger.info(f"  Total Indexes: {total_indexes}")
        logger.info(f"  Total Documents: {total_documents}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        return False


async def main():
    """Main entry point"""
    success = await verify_database()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
