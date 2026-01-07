"""
Agent Monitor Service
Tracks recent agent activities globally for the admin dashboard
"""

from typing import List, Dict, Any
from datetime import datetime
from collections import deque

class AgentActivityMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentActivityMonitor, cls).__new__(cls)
            # Use a deque to keep only the last 20 activities
            cls._instance.activities = deque(maxlen=20)
            print(f"DEBUG: AgentActivityMonitor singleton created at {id(cls._instance)}")
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AgentActivityMonitor()
        return cls._instance

    def log_activity(self, session_id: str, user_id: str, activity_type: str, message: str, data: Any = None):
        """Record an agent activity"""
        activity = {
            "timestamp": datetime.now().isoformat(),
            "session_id": str(session_id),
            "user_id": str(user_id),
            "type": activity_type, # 'thought', 'action', 'response', 'error'
            "message": str(message),
            "data": data
        }
        self.activities.appendleft(activity)
        print(f"DEBUG: Logged activity: {activity_type} for session {session_id}")

    def get_activities(self) -> List[Dict[str, Any]]:
        """Get the history of recent activities"""
        return list(self.activities)

# Global monitor instance
agent_monitor = AgentActivityMonitor()

