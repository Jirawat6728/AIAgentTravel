"""
MongoDB module
Provides MongoDB connection and database access
"""

from .connection import connect_to_mongo, close_mongo, get_db

__all__ = ["connect_to_mongo", "close_mongo", "get_db"]

