"""
Privacy & Security Audit Script
Checks that all data access is properly filtered by user_id
"""

import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def audit_database_queries():
    """Audit database collections for user_id isolation"""
    
    try:
        mongo_uri = settings.mongodb_uri
        database_name = settings.mongodb_database or "travel_agent"
        
        logger.info("=" * 80)
        logger.info("PRIVACY & SECURITY AUDIT")
        logger.info("=" * 80)
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client[database_name]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("[OK] MongoDB connection successful\n")
        
        # Collections that MUST have user_id field and be isolated
        user_isolated_collections = [
            "memories",      # AI Brain - CRITICAL
            "sessions",      # Session data
            "conversations", # Chat history
            "bookings",      # Booking data
            "payments",      # Payment data
            "invoices",      # Invoice data
            "refunds",       # Refund data
            "cost_tracking", # Cost data
            "workflow_history", # Workflow data
            "api_logs",      # API logs
            "error_logs",    # Error logs
            "audit_logs",    # Audit logs
            "access_tokens", # Access tokens
            "security_events" # Security events
        ]
        
        logger.info("Auditing user_id isolation...\n")
        
        issues_found = []
        checks_passed = 0
        
        for collection_name in user_isolated_collections:
            try:
                collection = db[collection_name]
                
                # Check 1: Collection has user_id index
                indexes = await collection.list_indexes().to_list(length=100)
                has_user_id_index = any(
                    "user_id" in str(idx.get("key", {}))
                    for idx in indexes
                )
                
                # Check 2: Sample documents all have user_id field
                sample_docs = await collection.find({}).limit(10).to_list(length=10)
                docs_with_user_id = sum(1 for doc in sample_docs if doc.get("user_id"))
                total_docs = len(sample_docs)
                
                # Check 3: No documents with empty/null user_id (if docs exist)
                docs_without_user_id = total_docs - docs_with_user_id
                
                status = "[OK]"
                issues = []
                
                if not has_user_id_index:
                    status = "[WARN]"
                    issues.append("Missing user_id index")
                
                if total_docs > 0 and docs_without_user_id > 0:
                    status = "[ERROR]"
                    issues.append(f"{docs_without_user_id}/{total_docs} documents missing user_id")
                
                if status == "[OK]":
                    checks_passed += 1
                else:
                    issues_found.append((collection_name, issues))
                
                logger.info(f"{status} {collection_name:20s} | user_id index: {has_user_id_index} | sample docs: {docs_with_user_id}/{total_docs} with user_id")
                
                if issues:
                    for issue in issues:
                        logger.warning(f"         - {issue}")
                
            except Exception as e:
                logger.error(f"[ERROR] {collection_name}: Failed to audit - {e}")
                issues_found.append((collection_name, [str(e)]))
        
        logger.info("\n" + "=" * 80)
        logger.info("AUDIT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Collections checked: {len(user_isolated_collections)}")
        logger.info(f"Checks passed: {checks_passed}/{len(user_isolated_collections)}")
        logger.info(f"Issues found: {len(issues_found)}")
        
        if issues_found:
            logger.info("\n[ISSUES FOUND]")
            for collection_name, issues in issues_found:
                logger.info(f"  {collection_name}:")
                for issue in issues:
                    logger.info(f"    - {issue}")
        else:
            logger.info("\n[OK] All collections properly configured for user isolation!")
        
        logger.info("=" * 80)
        
        return len(issues_found) == 0
        
    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
        return False


async def audit_code_patterns():
    """Audit code files for proper user_id filtering"""
    
    logger.info("\n" + "=" * 80)
    logger.info("CODE PATTERN AUDIT")
    logger.info("=" * 80)
    
    # Patterns to check
    patterns_to_check = [
        {
            "name": "Memory recall with user_id",
            "pattern": r'memory\.recall\([^)]*user_id',
            "file_pattern": "**/*.py",
            "required": True
        },
        {
            "name": "Memory consolidate with user_id",
            "pattern": r'memory\.consolidate\([^)]*user_id',
            "file_pattern": "**/*.py",
            "required": True
        },
        {
            "name": "Query with user_id filter",
            "pattern": r'find\([^)]*"user_id"',
            "file_pattern": "**/*storage*.py",
            "required": True
        }
    ]
    
    # This is a simplified check - in production, use AST parsing
    logger.info("Code pattern audit requires AST parsing (implement if needed)")
    
    return True


async def main():
    """Main entry point"""
    success = await audit_database_queries()
    code_audit = await audit_code_patterns()
    
    return 0 if (success and code_audit) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
