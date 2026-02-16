"""
อินเทอร์เฟซการจัดเก็บ - แบบ Repository
รองรับการย้ายไป PostgreSQL หรือ backend อื่นได้ง่าย
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from app.models.session import UserSession


class StorageInterface(ABC):
    """
    Abstract base class for storage implementations
    Repository Pattern for future database migration
    """
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session by session_id
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession if found, None otherwise
            
        Raises:
            StorageException: If storage operation fails
        """
        pass
    
    @abstractmethod
    async def save_session(self, session: UserSession) -> bool:
        """
        Save session to storage
        
        Args:
            session: UserSession object to save
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageException: If storage operation fails
        """
        pass
    
    @abstractmethod
    async def update_title(self, session_id: str, title: str) -> bool:
        """
        Update session title
        
        Args:
            session_id: Session identifier
            title: New title to set
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageException: If storage operation fails
        """
        pass

    @abstractmethod
    async def save_message(self, session_id: str, message: dict) -> bool:
        """
        Save a chat message to conversation history
        
        Args:
            session_id: Session identifier
            message: Message dictionary (role, content, timestamp, etc.)
            
        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """
        Get chat history for a session
        
        Args:
            session_id: Session identifier
            limit: Max number of messages to return
            
        Returns:
            List of message dictionaries
        """
        pass
