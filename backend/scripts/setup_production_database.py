"""
Production Database Setup Script
Creates all collections, indexes, and TTL policies
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel
from datetime import datetime
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Index Definitions
# =============================================================================

USER_INDEXES = [
    IndexModel([("user_id", 1)], unique=True, name="user_id_unique"),
    IndexModel([("email", 1)], unique=True, sparse=True, name="email_unique"),
    IndexModel([("last_active", -1)], name="last_active_idx"),
    IndexModel([("created_at", -1)], name="created_at_idx"),
    IndexModel([("is_active", 1), ("last_active", -1)], name="active_users_idx"),
]

SESSION_INDEXES = [
    IndexModel([("session_id", 1)], unique=True, name="session_id_unique"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("trip_id", 1)], name="trip_id_idx"),
    IndexModel([("last_updated", -1)], name="last_updated_idx"),
    IndexModel([("user_id", 1), ("last_updated", -1)], name="user_last_updated_idx"),
    # TTL index: Auto-delete sessions older than 90 days
    IndexModel([("last_updated", 1)], expireAfterSeconds=7776000, name="ttl_last_updated"),  # 90 days
]

CONVERSATION_INDEXES = [
    IndexModel([("session_id", 1)], name="session_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("updated_at", -1)], name="updated_at_idx"),
    IndexModel([("session_id", 1), ("updated_at", -1)], name="session_updated_idx"),
    # TTL index: Retain for 1 year
    IndexModel([("created_at", 1)], expireAfterSeconds=31536000, name="ttl_created_at"),  # 1 year
]

MEMORY_INDEXES = [
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("importance", -1)], name="importance_idx"),
    IndexModel([("user_id", 1), ("importance", -1)], name="user_importance_idx"),
    IndexModel([("category", 1)], name="category_idx"),
    IndexModel([("last_accessed", -1)], name="last_accessed_idx"),
    IndexModel([("user_id", 1), ("created_at", -1)], name="user_created_idx"),
]

BOOKING_INDEXES = [
    IndexModel([("booking_id", 1)], unique=True, sparse=True, name="booking_id_unique"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("trip_id", 1)], name="trip_id_idx"),
    IndexModel([("status", 1)], name="status_idx"),
    IndexModel([("payment_status", 1)], name="payment_status_idx"),
    IndexModel([("created_at", -1)], name="created_at_idx"),
    IndexModel([("user_id", 1), ("created_at", -1)], name="user_created_idx"),
    IndexModel([("status", 1), ("created_at", -1)], name="status_created_idx"),
]

PAYMENT_INDEXES = [
    IndexModel([("payment_id", 1)], unique=True, name="payment_id_unique"),
    IndexModel([("booking_id", 1)], name="booking_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("status", 1)], name="status_idx"),
    IndexModel([("created_at", -1)], name="created_at_idx"),
    IndexModel([("user_id", 1), ("created_at", -1)], name="user_created_idx"),
    IndexModel([("omise_charge_id", 1)], name="omise_charge_idx"),
]

INVOICE_INDEXES = [
    IndexModel([("invoice_id", 1)], unique=True, name="invoice_id_unique"),
    IndexModel([("invoice_number", 1)], unique=True, name="invoice_number_unique"),
    IndexModel([("booking_id", 1)], name="booking_id_idx"),
    IndexModel([("payment_id", 1)], name="payment_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("created_at", -1)], name="created_at_idx"),
]

REFUND_INDEXES = [
    IndexModel([("refund_id", 1)], unique=True, name="refund_id_unique"),
    IndexModel([("booking_id", 1)], name="booking_id_idx"),
    IndexModel([("payment_id", 1)], name="payment_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("status", 1)], name="status_idx"),
    IndexModel([("requested_at", -1)], name="requested_at_idx"),
]

COST_TRACKING_INDEXES = [
    IndexModel([("session_id", 1)], name="session_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("created_at", -1)], name="created_at_idx"),
    IndexModel([("user_id", 1), ("created_at", -1)], name="user_created_idx"),
    IndexModel([("brain_type", 1), ("created_at", -1)], name="brain_created_idx"),
    # TTL index: Retain for 1 year
    IndexModel([("created_at", 1)], expireAfterSeconds=31536000, name="ttl_created_at"),  # 1 year
]

WORKFLOW_HISTORY_INDEXES = [
    IndexModel([("session_id", 1)], name="session_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("timestamp", -1)], name="timestamp_idx"),
    IndexModel([("workflow_stage", 1), ("timestamp", -1)], name="stage_timestamp_idx"),
    # TTL index: Retain for 90 days
    IndexModel([("timestamp", 1)], expireAfterSeconds=7776000, name="ttl_timestamp"),  # 90 days
]

API_LOG_INDEXES = [
    IndexModel([("session_id", 1)], name="session_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("api_name", 1), ("timestamp", -1)], name="api_timestamp_idx"),
    IndexModel([("timestamp", -1)], name="timestamp_idx"),
    IndexModel([("response_status", 1), ("timestamp", -1)], name="status_timestamp_idx"),
    # TTL index: Retain for 30 days
    IndexModel([("timestamp", 1)], expireAfterSeconds=2592000, name="ttl_timestamp"),  # 30 days
]

ERROR_LOG_INDEXES = [
    IndexModel([("session_id", 1)], name="session_id_idx"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("error_type", 1), ("timestamp", -1)], name="error_timestamp_idx"),
    IndexModel([("severity", 1), ("timestamp", -1)], name="severity_timestamp_idx"),
    IndexModel([("resolved", 1), ("timestamp", -1)], name="resolved_timestamp_idx"),
    IndexModel([("timestamp", -1)], name="timestamp_idx"),
    # TTL index: Retain for 90 days
    IndexModel([("timestamp", 1)], expireAfterSeconds=7776000, name="ttl_timestamp"),  # 90 days
]

AUDIT_LOG_INDEXES = [
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("action", 1), ("timestamp", -1)], name="action_timestamp_idx"),
    IndexModel([("resource_type", 1), ("resource_id", 1)], name="resource_idx"),
    IndexModel([("timestamp", -1)], name="timestamp_idx"),
    # TTL index: Retain for 2 years (compliance)
    IndexModel([("timestamp", 1)], expireAfterSeconds=63072000, name="ttl_timestamp"),  # 2 years
]

ACCESS_TOKEN_INDEXES = [
    IndexModel([("token_id", 1)], unique=True, name="token_id_unique"),
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("expires_at", 1)], name="expires_at_idx"),
    IndexModel([("is_active", 1), ("expires_at", 1)], name="active_expires_idx"),
    # TTL index: Auto-delete expired tokens
    IndexModel([("expires_at", 1)], expireAfterSeconds=0, name="ttl_expires_at"),
]

SECURITY_EVENT_INDEXES = [
    IndexModel([("user_id", 1)], name="user_id_idx"),
    IndexModel([("event_type", 1), ("timestamp", -1)], name="event_timestamp_idx"),
    IndexModel([("severity", 1), ("timestamp", -1)], name="severity_timestamp_idx"),
    IndexModel([("ip_address", 1), ("timestamp", -1)], name="ip_timestamp_idx"),
    IndexModel([("resolved", 1), ("timestamp", -1)], name="resolved_timestamp_idx"),
    # TTL index: Retain for 1 year
    IndexModel([("timestamp", 1)], expireAfterSeconds=31536000, name="ttl_timestamp"),  # 1 year
]


# =============================================================================
# Setup Functions
# =============================================================================

async def create_collection_indexes(db, collection_name: str, indexes: list):
    """Create indexes for a collection"""
    try:
        collection = db[collection_name]
        
        # Try to create all indexes at once first
        try:
            result = await collection.create_indexes(indexes)
            logger.info(f"[OK] Created {len(result)} indexes for '{collection_name}' collection")
            return result
        except Exception as batch_err:
            # If batch creation fails, try one by one
            if "already exists" in str(batch_err).lower() or "IndexOptionsConflict" in str(batch_err):
                logger.info(f"[INFO] Some indexes may already exist for '{collection_name}', creating one by one...")
                created = 0
                skipped = 0
                
                for idx_model in indexes:
                    try:
                        result = await collection.create_indexes([idx_model])
                        if result:
                            created += 1
                    except Exception as idx_err:
                        if "already exists" in str(idx_err).lower() or "IndexOptionsConflict" in str(idx_err):
                            skipped += 1
                            logger.debug(f"Index already exists, skipping...")
                        else:
                            logger.warning(f"Could not create index: {idx_err}")
                
                logger.info(f"[OK] Created {created} new indexes for '{collection_name}' collection (skipped {skipped} existing)")
                return list(range(created))  # Return list of created count
            else:
                raise batch_err
                
    except Exception as e:
        logger.error(f"[ERROR] Failed to create indexes for '{collection_name}': {e}")
        # Don't raise - continue with other collections
        return []


async def verify_indexes(db, collection_name: str):
    """Verify indexes were created"""
    try:
        collection = db[collection_name]
        indexes = await collection.list_indexes().to_list(length=100)
        logger.info(f"'{collection_name}' has {len(indexes)} indexes")
        for idx in indexes:
            logger.debug(f"   - {idx.get('name')}: {idx.get('key')}")
        return indexes
    except Exception as e:
        logger.error(f"[ERROR] Failed to verify indexes for '{collection_name}': {e}")
        return []


async def setup_production_database():
    """Setup production database with all collections and indexes"""
    try:
        # Connect to MongoDB
        mongo_uri = settings.mongodb_uri
        database_name = settings.mongodb_database or "travel_agent"
        
        logger.info(f"Connecting to MongoDB: {database_name}")
        client = AsyncIOMotorClient(mongo_uri)
        db = client[database_name]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("[OK] MongoDB connection successful")
        
        # Create indexes for each collection
        collections_config = [
            ("users", USER_INDEXES),
            ("sessions", SESSION_INDEXES),
            ("conversations", CONVERSATION_INDEXES),
            ("memories", MEMORY_INDEXES),
            ("bookings", BOOKING_INDEXES),
            ("payments", PAYMENT_INDEXES),
            ("invoices", INVOICE_INDEXES),
            ("refunds", REFUND_INDEXES),
            ("cost_tracking", COST_TRACKING_INDEXES),
            ("workflow_history", WORKFLOW_HISTORY_INDEXES),
            ("api_logs", API_LOG_INDEXES),
            ("error_logs", ERROR_LOG_INDEXES),
            ("audit_logs", AUDIT_LOG_INDEXES),
            ("access_tokens", ACCESS_TOKEN_INDEXES),
            ("security_events", SECURITY_EVENT_INDEXES),
        ]
        
        logger.info(f"Setting up {len(collections_config)} collections...")
        
        for collection_name, indexes in collections_config:
            logger.info(f"\nSetting up '{collection_name}' collection...")
            await create_collection_indexes(db, collection_name, indexes)
            await verify_indexes(db, collection_name)
        
        logger.info("\n[OK] Production database setup complete!")
        
        # Summary
        logger.info("\n📊 Summary:")
        for collection_name, _ in collections_config:
            indexes = await verify_indexes(db, collection_name)
            logger.info(f"   {collection_name}: {len(indexes)} indexes")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}", exc_info=True)
        return False


async def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("PRODUCTION DATABASE SETUP")
    logger.info("=" * 80)
    logger.info(f"Database: {settings.mongodb_database or 'travel_agent'}")
    logger.info(f"MongoDB URI: {settings.mongodb_uri[:50]}...")
    logger.info("=" * 80)
    
    success = await setup_production_database()
    
    if success:
        logger.info("\n[SUCCESS] Setup completed successfully!")
        return 0
    else:
        logger.error("\n[FAILED] Setup failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
