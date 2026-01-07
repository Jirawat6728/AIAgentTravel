"""
Async JSON File Storage using aiofiles
Non-blocking I/O for concurrent user support
"""

from __future__ import annotations
from typing import Optional
import json
import aiofiles
from pathlib import Path

from app.storage.interface import StorageInterface
from app.models.session import UserSession
from app.core.config import settings
from app.core.exceptions import StorageException
from app.core.logging import get_logger

logger = get_logger(__name__)


class JsonFileStorage(StorageInterface):
    """
    Async JSON File Storage Implementation
    Uses aiofiles for non-blocking file I/O
    Stores sessions as individual JSON files in ./data/sessions/
    """
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize JSON File Storage
        
        Args:
            sessions_dir: Directory to store session files (defaults to settings.sessions_dir)
        """
        self.sessions_dir = sessions_dir or settings.sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"JsonFileStorage initialized with sessions_dir: {self.sessions_dir}")
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session file (sanitized)"""
        # Sanitize session_id for filename
        safe_id = session_id.replace("::", "_").replace("/", "_").replace("\\", "_")
        return self.sessions_dir / f"{safe_id}.json"
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session from JSON file (async, non-blocking)
        Creates new session if file doesn't exist
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession object
            
        Raises:
            StorageException: If file read fails or data is corrupted
        """
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            logger.info(f"Session file not found for {session_id}, creating new session")
            # Extract user_id from session_id (format: user_id::conversation_id)
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            session = UserSession(session_id=session_id, user_id=user_id)
            await self.save_session(session)
            return session
        
        try:
            async with aiofiles.open(session_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            # Validate with Pydantic - catches corrupted data instantly
            session = UserSession.from_dict(data)
            logger.debug(f"Loaded session {session_id} from disk")
            return session
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in session file for {session_id}: {e}")
            # Create new session if file is corrupted
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            session = UserSession(session_id=session_id, user_id=user_id)
            await self.save_session(session)
            return session
        
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to load session {session_id}: {e}") from e
    
    async def save_session(self, session: UserSession) -> bool:
        """
        Save session to JSON file (async, non-blocking, atomic write)
        
        Args:
            session: UserSession object to save
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If file write fails
        """
        try:
            session.update_timestamp()
            session_path = self._get_session_path(session.session_id)
            
            # Write to temporary file first, then rename (atomic write)
            temp_path = session_path.with_suffix('.tmp')
            
            # Serialize with Pydantic validation
            data = session.to_dict()
            
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            
            # Atomic rename
            temp_path.replace(session_path)
            
            logger.debug(f"Saved session {session.session_id} to disk")
            return True
        
        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to save session {session.session_id}: {e}") from e
    
    async def update_title(self, session_id: str, title: str) -> bool:
        """
        Update session title (async, non-blocking)
        
        Args:
            session_id: Session identifier
            title: New title to set
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If update fails
        """
        try:
            # Load session
            session = await self.get_session(session_id)
            if not session:
                logger.error(f"Session not found for title update: {session_id}")
                raise StorageException(f"Session not found: {session_id}")
            
            # Update title
            session.title = title
            session.update_timestamp()
            
            # Save session
            await self.save_session(session)
            
            logger.info(f"Updated title for session {session_id}: {title}")
            return True
        
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Error updating title for session {session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to update title for session {session_id}: {e}") from e
