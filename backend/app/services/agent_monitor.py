"""
เซอร์วิสตรวจสอบ Agent
ติดตามกิจกรรมล่าสุดของ agent ทั้งระบบ สำหรับแดชบอร์ดแอดมิน
"""

from typing import List, Dict, Any
from datetime import datetime
from collections import deque

class AgentActivityMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentActivityMonitor, cls).__new__(cls)
            # Keep a larger rolling window for monitoring dashboards/telemetry
            cls._instance.activities = deque(maxlen=500)
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

    def get_search_relaxed_summary(self) -> Dict[str, Any]:
        """Aggregate relaxed-search telemetry from recent activities."""
        total_relaxed = 0
        by_reason: Dict[str, int] = {}
        no_result_after_relax = 0

        for activity in self.activities:
            a_type = activity.get("type")
            data = activity.get("data") or {}
            if a_type == "search_relaxed":
                total_relaxed += 1
                reason = str(data.get("reason") or "unknown")
                by_reason[reason] = by_reason.get(reason, 0) + 1
            elif a_type == "search_no_results_after_relax":
                no_result_after_relax += 1

        return {
            "total_relaxed": total_relaxed,
            "by_reason": by_reason,
            "no_result_after_relax": no_result_after_relax,
            "window_size": len(self.activities),
        }

# Global monitor instance
agent_monitor = AgentActivityMonitor()

