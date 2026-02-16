"""
โมดูล Reinforcement Learning สำหรับ AI Travel Agent
เรียนรู้จากการโต้ตอบของผู้ใช้และปรับปรุงการแนะนำให้ดีขึ้นในแต่ละรอบ
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RewardSignal:
    """Reward signal from user interaction"""
    timestamp: datetime
    action_type: str  # "select_option", "book", "reject", "edit"
    slot_name: str
    option_index: int
    reward_value: float  # -1.0 to 1.0
    context: Dict[str, Any]


class RewardFunction:
    """
    Reward Function สำหรับประเมินความพึงพอใจของผู้ใช้ในระยะยาว
    
    Reward signals:
    - Positive: User selects option, completes booking, positive feedback
    - Negative: User rejects option, cancels booking, negative feedback
    """
    
    # Reward values
    REWARD_SELECT_OPTION = 0.3  # User selects an option
    REWARD_COMPLETE_BOOKING = 1.0  # User completes booking
    REWARD_POSITIVE_FEEDBACK = 0.5  # User gives positive feedback
    REWARD_REJECT_OPTION = -0.2  # User rejects an option
    REWARD_CANCEL_BOOKING = -0.5  # User cancels booking
    REWARD_NEGATIVE_FEEDBACK = -0.3  # User gives negative feedback
    REWARD_EDIT_SELECTION = -0.1  # User edits selection (minor negative)
    
    @staticmethod
    def calculate_reward(
        action_type: str,
        slot_name: str,
        option_index: int,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        คำนวณ reward จาก user action
        
        Args:
            action_type: Type of action ("select_option", "book", "reject", "edit", "feedback")
            slot_name: Slot name (e.g., "flights_outbound", "accommodation")
            option_index: Index of selected option
            context: Additional context (e.g., feedback score, booking status)
            
        Returns:
            Reward value (-1.0 to 1.0)
        """
        context = context or {}
        
        if action_type == "select_option":
            return RewardFunction.REWARD_SELECT_OPTION
        elif action_type == "book" or action_type == "complete_booking":
            return RewardFunction.REWARD_COMPLETE_BOOKING
        elif action_type == "positive_feedback":
            # Scale by feedback score if provided
            feedback_score = context.get("feedback_score", 1.0)
            return RewardFunction.REWARD_POSITIVE_FEEDBACK * feedback_score
        elif action_type == "reject" or action_type == "reject_option":
            return RewardFunction.REWARD_REJECT_OPTION
        elif action_type == "cancel" or action_type == "cancel_booking":
            return RewardFunction.REWARD_CANCEL_BOOKING
        elif action_type == "negative_feedback":
            feedback_score = abs(context.get("feedback_score", -1.0))
            return RewardFunction.REWARD_NEGATIVE_FEEDBACK * feedback_score
        elif action_type == "edit" or action_type == "edit_selection":
            return RewardFunction.REWARD_EDIT_SELECTION
        else:
            return 0.0  # Unknown action


class ReinforcementLearner:
    """
    Reinforcement Learning Agent
    ใช้เทคนิค Reinforcement Learning เพื่อเรียนรู้จากการโต้ตอบของผู้ใช้
    และปรับปรุงการแนะนำให้ดีขึ้นในแต่ละรอบ
    """
    
    def __init__(self, discount_factor: float = 0.9, total_rounds: int = 10):
        """
        Initialize RL Agent
        
        Args:
            discount_factor: ค่าการลดทอน (Discount Factor, 0 < γ < 1)
            total_rounds: จำนวนรอบการเรียนรู้ทั้งหมด (T)
        """
        self.gamma = discount_factor  # γ (gamma)
        self.T = total_rounds  # T (total rounds)
        self.reward_history: List[RewardSignal] = []
        self.logger = get_logger(__name__)
        
        self.logger.info(f"ReinforcementLearner initialized: γ={self.gamma}, T={self.T}")
    
    def calculate_expected_return(
        self,
        state: Dict[str, Any],
        time_step: int = 0
    ) -> float:
        """
        คำนวณค่ารางวัลคาดหวัง (Expected Return)
        
        สมการ: Rt = E[ Σ_{k=0}^{T-t} γ^k r_{t+k+1} | S_t ] (3)
        
        โดยที่:
        - Rt = ค่ารางวัลรวมที่คาดหวังในสถานะ St
        - rt = ค่ารางวัลที่ได้รับในช่วงเวลา t
        - γ = ค่าการลดทอน (Discount Factor, 0 < γ < 1)
        - T = จำนวนรอบการเรียนรู้ทั้งหมด
        
        Args:
            state: Current state S_t
            time_step: Current time step t
            
        Returns:
            Expected return R_t
        """
        if time_step >= self.T:
            return 0.0
        
        # Calculate expected return: Σ_{k=0}^{T-t} γ^k r_{t+k+1}
        expected_return = 0.0
        
        # Use historical rewards to estimate future rewards
        # If we have reward history, use it to estimate future rewards
        if self.reward_history:
            # Average reward from similar states
            similar_rewards = [
                r.reward_value for r in self.reward_history
                if self._is_similar_state(r.context, state)
            ]
            
            if similar_rewards:
                avg_reward = sum(similar_rewards) / len(similar_rewards)
            else:
                # Use overall average if no similar states
                avg_reward = sum(r.reward_value for r in self.reward_history) / len(self.reward_history)
        else:
            # No history yet, use default optimistic estimate
            avg_reward = 0.1  # Small positive default
        
        # Calculate discounted sum: Σ_{k=0}^{T-t} γ^k * avg_reward
        for k in range(self.T - time_step):
            discounted_reward = (self.gamma ** k) * avg_reward
            expected_return += discounted_reward
        
        return expected_return
    
    def _is_similar_state(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> bool:
        """Check if two states are similar"""
        # Compare key features
        key_features = ["slot_name", "destination", "trip_type"]
        for feature in key_features:
            if state1.get(feature) != state2.get(feature):
                return False
        return True
    
    def record_reward(
        self,
        action_type: str,
        slot_name: str,
        option_index: int,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        บันทึก reward จาก user interaction
        
        Args:
            action_type: Type of action
            slot_name: Slot name
            option_index: Option index
            context: Additional context
        """
        reward_value = RewardFunction.calculate_reward(
            action_type, slot_name, option_index, context
        )
        
        reward_signal = RewardSignal(
            timestamp=datetime.utcnow(),
            action_type=action_type,
            slot_name=slot_name,
            option_index=option_index,
            reward_value=reward_value,
            context=context or {}
        )
        
        self.reward_history.append(reward_signal)
        
        # Keep only last T rounds
        if len(self.reward_history) > self.T:
            self.reward_history = self.reward_history[-self.T:]
        
        self.logger.info(
            f"RL: Recorded reward {reward_value:.2f} for {action_type} "
            f"on {slot_name}[{option_index}]"
        )
    
    def get_expected_return_for_option(
        self,
        slot_name: str,
        option_index: int,
        state: Dict[str, Any]
    ) -> float:
        """
        คำนวณ expected return สำหรับ option นี้
        
        Args:
            slot_name: Slot name
            option_index: Option index
            state: Current state
            
        Returns:
            Expected return value
        """
        # Create context for this option
        option_state = {
            **state,
            "slot_name": slot_name,
            "option_index": option_index
        }
        
        return self.calculate_expected_return(option_state)
    
    def get_reward_statistics(self) -> Dict[str, Any]:
        """Get statistics about reward history"""
        if not self.reward_history:
            return {
                "total_rewards": 0,
                "average_reward": 0.0,
                "positive_rewards": 0,
                "negative_rewards": 0
            }
        
        rewards = [r.reward_value for r in self.reward_history]
        positive = sum(1 for r in rewards if r > 0)
        negative = sum(1 for r in rewards if r < 0)
        
        return {
            "total_rewards": len(self.reward_history),
            "average_reward": sum(rewards) / len(rewards),
            "positive_rewards": positive,
            "negative_rewards": negative,
            "positive_ratio": positive / len(self.reward_history) if self.reward_history else 0.0
        }


# Global RL instance
_rl_learner: Optional[ReinforcementLearner] = None

def get_rl_learner() -> ReinforcementLearner:
    """Get or create global RL learner instance"""
    global _rl_learner
    if _rl_learner is None:
        _rl_learner = ReinforcementLearner(discount_factor=0.9, total_rounds=10)
    return _rl_learner
