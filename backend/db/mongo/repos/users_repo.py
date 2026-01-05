"""
Users Repository
Handles user profile data access with full CRUD operations
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import motor.motor_asyncio
from bson import ObjectId


class UsersRepo:
    """Repository for user operations with full CRUD support"""
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users
    
    async def ensure_indexes(self):
        """Create indexes for better query performance"""
        try:
            await self.collection.create_index("email", unique=True)
            await self.collection.create_index("google_id", unique=True, sparse=True)
            await self.collection.create_index("created_at")
        except Exception as e:
            import logging
            logging.warning(f"Failed to create indexes: {e}")
    
    # ===== CREATE =====
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            user_data: Dictionary containing user information
                - email: str (required)
                - name: str (optional)
                - google_id: str (optional)
                - picture: str (optional)
        
        Returns:
            Created user document with _id as string
        """
        # Add timestamps
        user_data.setdefault("created_at", datetime.utcnow())
        user_data.setdefault("updated_at", datetime.utcnow())
        
        result = await self.collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Return created user
        user = await self.get_by_id(user_id)
        return user
    
    # ===== READ =====
    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id: User ID (string)
        
        Returns:
            User document or None if not found
        """
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user and "_id" in user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email
        
        Args:
            email: User email
        
        Returns:
            User document or None if not found
        """
        user = await self.collection.find_one({"email": email})
        if user and "_id" in user:
            user["_id"] = str(user["_id"])
        return user
    
    async def get_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Google ID
        
        Args:
            google_id: Google user ID
        
        Returns:
            User document or None if not found
        """
        user = await self.collection.find_one({"google_id": google_id})
        if user and "_id" in user:
            user["_id"] = str(user["_id"])
        return user
    
    async def get_all(
        self,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all users (admin function)
        
        Args:
            limit: Maximum number of results (default: 100)
            skip: Number of results to skip (default: 0)
        
        Returns:
            List of user documents
        """
        cursor = self.collection.find({}).sort("created_at", -1).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for user in users:
            if "_id" in user:
                user["_id"] = str(user["_id"])
        
        return users
    
    async def count(self) -> int:
        """
        Count total users
        
        Returns:
            Number of users
        """
        return await self.collection.count_documents({})
    
    # ===== UPDATE =====
    async def update(
        self,
        user_id: str,
        updates: Dict[str, Any],
        partial: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Update a user
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            partial: If True, use $set (partial update). If False, replace entire document.
        
        Returns:
            Updated user document or None if not found
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            if partial:
                result = await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": updates}
                )
            else:
                # Replace entire document
                updates["_id"] = ObjectId(user_id)
                result = await self.collection.replace_one(
                    {"_id": ObjectId(user_id)},
                    updates
                )
            
            if result.modified_count > 0:
                return await self.get_by_id(user_id)
            return None
        except Exception as e:
            import logging
            logging.error(f"Failed to update user {user_id}: {e}")
            return None
    
    async def update_profile(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        dob: Optional[str] = None,
        gender: Optional[str] = None,
        passport_no: Optional[str] = None,
        passport_expiry: Optional[str] = None,
        nationality: Optional[str] = None,
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        province: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update user profile (convenience method)
        
        Args:
            user_id: User ID
            first_name: First name
            last_name: Last name
            phone: Phone number
            dob: Date of birth
            gender: Gender
            passport_no: Passport number
            passport_expiry: Passport expiry date
            nationality: Nationality
            address_line1: Address line 1
            address_line2: Address line 2
            city: City
            province: Province
            postal_code: Postal code
            country: Country
        
        Returns:
            Updated user document or None if not found
        """
        updates = {}
        if first_name is not None:
            updates["first_name"] = first_name
        if last_name is not None:
            updates["last_name"] = last_name
        if phone is not None:
            updates["phone"] = phone
        if dob is not None:
            updates["dob"] = dob
        if gender is not None:
            updates["gender"] = gender
        if passport_no is not None:
            updates["passport_no"] = passport_no
        if passport_expiry is not None:
            updates["passport_expiry"] = passport_expiry
        if nationality is not None:
            updates["nationality"] = nationality
        if address_line1 is not None:
            updates["address_line1"] = address_line1
        if address_line2 is not None:
            updates["address_line2"] = address_line2
        if city is not None:
            updates["city"] = city
        if province is not None:
            updates["province"] = province
        if postal_code is not None:
            updates["postal_code"] = postal_code
        if country is not None:
            updates["country"] = country
        
        if updates:
            return await self.update(user_id, updates)
        return await self.get_by_id(user_id)
    
    # ===== DELETE =====
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user (soft delete by default - sets active to False)
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Soft delete: set active to False
            result = await self.update(
                user_id,
                {"active": False, "deleted_at": datetime.utcnow()}
            )
            return result is not None
        except Exception as e:
            import logging
            logging.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    async def hard_delete(self, user_id: str) -> bool:
        """
        Permanently delete a user from database
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted successfully, False otherwise
        
        Warning: This permanently removes the user. Use with caution.
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception as e:
            import logging
            logging.error(f"Failed to hard delete user {user_id}: {e}")
            return False

