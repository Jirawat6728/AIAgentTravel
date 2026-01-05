"""
Database module
Provides database access (MongoDB, and potentially other databases in the future)
"""

# MongoDB imports (backward compatibility)
from db.mongo import connect_to_mongo, close_mongo, get_db
from db.mongo.repos import BookingsRepo, UsersRepo, SessionsRepo

__all__ = [
    "connect_to_mongo",
    "close_mongo",
    "get_db",
    "BookingsRepo",
    "UsersRepo",
    "SessionsRepo",
]
