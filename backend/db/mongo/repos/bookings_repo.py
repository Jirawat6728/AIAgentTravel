"""
Bookings Repository
Handles booking data access with full CRUD operations
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import motor.motor_asyncio
from bson import ObjectId


class BookingsRepo:
    """Repository for booking operations with full CRUD support"""
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.bookings
    
    async def ensure_indexes(self):
        """Create indexes for better query performance"""
        try:
            await self.collection.create_index("user_id")
            await self.collection.create_index("status")
            await self.collection.create_index("created_at")
            await self.collection.create_index([("user_id", 1), ("status", 1)])
        except Exception as e:
            import logging
            logging.warning(f"Failed to create indexes: {e}")
    
    # ===== CREATE =====
    async def create(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new booking
        
        Args:
            booking_data: Dictionary containing booking information
                - user_id: str (required)
                - trip_id: str (optional)
                - plan: dict (required)
                - travel_slots: dict (optional)
                - user_profile: dict (optional)
                - total_price: float (required)
                - currency: str (default: "THB")
                - status: str (default: "pending_payment")
        
        Returns:
            Created booking document with _id as string
        """
        # Add timestamps
        booking_data.setdefault("created_at", datetime.utcnow())
        booking_data.setdefault("updated_at", datetime.utcnow())
        booking_data.setdefault("currency", "THB")
        booking_data.setdefault("status", "pending_payment")
        
        result = await self.collection.insert_one(booking_data)
        booking_id = str(result.inserted_id)
        
        # Return created booking
        booking = await self.get_by_id(booking_id)
        return booking
    
    # ===== READ =====
    async def get_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        Get booking by ID
        
        Args:
            booking_id: Booking ID (string)
        
        Returns:
            Booking document or None if not found
        """
        try:
            booking = await self.collection.find_one({"_id": ObjectId(booking_id)})
            if booking and "_id" in booking:
                booking["_id"] = str(booking["_id"])
            return booking
        except Exception:
            return None
    
    async def get_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get bookings by user ID
        
        Args:
            user_id: User ID
            status: Optional status filter (e.g., "confirmed", "pending_payment")
            limit: Maximum number of results (default: 50)
            skip: Number of results to skip (default: 0)
        
        Returns:
            List of booking documents
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        bookings = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for booking in bookings:
            if "_id" in booking:
                booking["_id"] = str(booking["_id"])
        
        return bookings
    
    async def get_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all bookings (admin function)
        
        Args:
            status: Optional status filter
            limit: Maximum number of results (default: 100)
            skip: Number of results to skip (default: 0)
        
        Returns:
            List of booking documents
        """
        query = {}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        bookings = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for booking in bookings:
            if "_id" in booking:
                booking["_id"] = str(booking["_id"])
        
        return bookings
    
    async def count(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count bookings
        
        Args:
            user_id: Optional user ID filter
            status: Optional status filter
        
        Returns:
            Number of bookings matching the criteria
        """
        query = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        
        return await self.collection.count_documents(query)
    
    # ===== UPDATE =====
    async def update(
        self,
        booking_id: str,
        updates: Dict[str, Any],
        partial: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Update a booking
        
        Args:
            booking_id: Booking ID
            updates: Dictionary of fields to update
            partial: If True, use $set (partial update). If False, replace entire document.
        
        Returns:
            Updated booking document or None if not found
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            if partial:
                result = await self.collection.update_one(
                    {"_id": ObjectId(booking_id)},
                    {"$set": updates}
                )
            else:
                # Replace entire document
                updates["_id"] = ObjectId(booking_id)
                result = await self.collection.replace_one(
                    {"_id": ObjectId(booking_id)},
                    updates
                )
            
            if result.modified_count > 0:
                return await self.get_by_id(booking_id)
            return None
        except Exception as e:
            import logging
            logging.error(f"Failed to update booking {booking_id}: {e}")
            return None
    
    async def update_status(
        self,
        booking_id: str,
        status: str,
        payment_status: Optional[str] = None,
        amadeus_booking_reference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update booking status (convenience method)
        
        Args:
            booking_id: Booking ID
            status: New status (e.g., "confirmed", "cancelled", "pending_payment")
            payment_status: Optional payment status
            amadeus_booking_reference: Optional Amadeus booking reference
            notes: Optional notes
        
        Returns:
            True if updated successfully, False otherwise
        """
        updates = {"status": status}
        if payment_status:
            updates["payment_status"] = payment_status
        if amadeus_booking_reference:
            updates["amadeus_booking_reference"] = amadeus_booking_reference
        if notes:
            updates["notes"] = notes
        
        updates["updated_at"] = datetime.utcnow()
        
        result = await self.update(booking_id, updates)
        return result is not None
    
    # ===== DELETE =====
    async def delete(self, booking_id: str) -> bool:
        """
        Delete a booking (soft delete by default - sets status to "deleted")
        
        Args:
            booking_id: Booking ID
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Soft delete: set status to "deleted" instead of actually deleting
            result = await self.update_status(
                booking_id,
                status="deleted",
                notes="Booking deleted by user"
            )
            return result
        except Exception as e:
            import logging
            logging.error(f"Failed to delete booking {booking_id}: {e}")
            return False
    
    async def hard_delete(self, booking_id: str) -> bool:
        """
        Permanently delete a booking from database
        
        Args:
            booking_id: Booking ID
        
        Returns:
            True if deleted successfully, False otherwise
        
        Warning: This permanently removes the booking. Use with caution.
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(booking_id)})
            return result.deleted_count > 0
        except Exception as e:
            import logging
            logging.error(f"Failed to hard delete booking {booking_id}: {e}")
            return False
    
    async def delete_by_user(self, user_id: str, status: Optional[str] = None) -> int:
        """
        Delete multiple bookings by user ID
        
        Args:
            user_id: User ID
            status: Optional status filter (only delete bookings with this status)
        
        Returns:
            Number of bookings deleted
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        # Soft delete: update status to "deleted"
        result = await self.collection.update_many(
            query,
            {
                "$set": {
                    "status": "deleted",
                    "updated_at": datetime.utcnow(),
                    "notes": "Bulk deleted by user"
                }
            }
        )
        return result.modified_count
