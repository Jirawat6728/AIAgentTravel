"""ติดตามต้นทุนการใช้ LLM (โทเค็น/ราคา) ตามโมเดลและเซสชัน."""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ModelType(str, Enum):
    """LLM Model types with pricing"""
    GEMINI_FLASH = "FLASH"
    GEMINI_PRO = "PRO"

def _get_model_pricing() -> Dict[str, Dict[str, float]]:
    """Get model pricing dictionary using model names from .env"""
    # Pricing per 1M tokens (in USD) - Updated 2025 rates
    return {
        settings.gemini_flash_model: {"input": 0.075, "output": 0.30},
        settings.gemini_pro_model: {"input": 1.25, "output": 5.00},
        settings.gemini_ultra_model: {"input": 2.50, "output": 10.00},
    }


# Get pricing from settings (initialized after settings is available)
MODEL_PRICING: Dict[str, Dict[str, float]] = {}


@dataclass
class LLMCall:
    """Single LLM call record"""
    timestamp: str
    model: str
    brain_type: str  # "controller", "responder", "intelligence", etc.
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    latency_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class SessionCostSummary:
    """Cost summary for a session"""
    session_id: str
    user_id: str
    mode: str  # "normal" or "agent"
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    calls: List[LLMCall] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "mode": self.mode,
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_cost_thb": round(self.total_cost_usd * 35, 2),  # Convert to THB (approx rate)
            "calls": [
                {
                    "timestamp": call.timestamp,
                    "model": call.model,
                    "brain_type": call.brain_type,
                    "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens,
                    "total_tokens": call.total_tokens,
                    "cost_usd": round(call.estimated_cost_usd, 6),
                    "latency_ms": call.latency_ms,
                    "success": call.success
                }
                for call in self.calls
            ],
            "started_at": self.started_at,
            "last_updated": self.last_updated
        }


class CostTracker:
    """
    Production-grade cost tracker for LLM usage
    
    Features:
    - Per-session cost tracking
    - Real-time token counting
    - Cost estimation with multiple models
    - Budget limits and alerts
    - Export to JSON for analytics
    """
    
    def __init__(self):
        """Initialize cost tracker"""
        self._session_costs: Dict[str, SessionCostSummary] = {}
        # Initialize MODEL_PRICING from settings
        global MODEL_PRICING
        MODEL_PRICING = _get_model_pricing()
        logger.info(f"CostTracker initialized with models: {list(MODEL_PRICING.keys())}")
    
    def track_llm_call(
        self,
        session_id: str,
        user_id: str,
        model: str,
        brain_type: str,
        input_tokens: int,
        output_tokens: int,
        mode: str = "normal",
        latency_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> float:
        """
        Track a single LLM call and return estimated cost
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            model: Model name (e.g., "gemini-3.0-flash")
            brain_type: Type of brain (controller, responder, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            mode: Chat mode (normal or agent)
            latency_ms: Optional latency in milliseconds
            success: Whether call succeeded
            error: Optional error message
            
        Returns:
            Estimated cost in USD
        """
        # Calculate cost
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens
        
        # Create call record
        call = LLMCall(
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            brain_type=brain_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
            success=success,
            error=error
        )
        
        # Get or create session summary
        if session_id not in self._session_costs:
            self._session_costs[session_id] = SessionCostSummary(
                session_id=session_id,
                user_id=user_id,
                mode=mode
            )
        
        summary = self._session_costs[session_id]
        
        # Update summary
        summary.total_calls += 1
        summary.total_input_tokens += input_tokens
        summary.total_output_tokens += output_tokens
        summary.total_tokens += total_tokens
        summary.total_cost_usd += cost
        summary.calls.append(call)
        summary.last_updated = datetime.utcnow().isoformat()
        
        # Log the call
        logger.info(
            f"[COST] {brain_type.upper()} - Model: {model}, "
            f"Tokens: {input_tokens}→{output_tokens} ({total_tokens} total), "
            f"Cost: ${cost:.6f} (฿{cost*35:.2f}), "
            f"Session Total: ${summary.total_cost_usd:.6f}",
            extra={
                "session_id": session_id,
                "user_id": user_id,
                "model": model,
                "brain_type": brain_type
            }
        )
        
        return cost
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model call"""
        # Try to find pricing by matching model name directly
        pricing = MODEL_PRICING.get(model)
        
        # If not found, try to match by model type keywords
        if not pricing:
            model_lower = model.lower()
            if "flash" in model_lower:
                pricing = MODEL_PRICING.get(settings.gemini_flash_model)
            elif "pro" in model_lower:
                pricing = MODEL_PRICING.get(settings.gemini_pro_model)
            elif "ultra" in model_lower:
                pricing = MODEL_PRICING.get(settings.gemini_ultra_model)
        
        # Default to Gemini Flash if not found
        if not pricing:
            logger.warning(f"Unknown model '{model}', defaulting to {settings.gemini_flash_model} pricing")
            pricing = MODEL_PRICING.get(settings.gemini_flash_model, {"input": 0.075, "output": 0.30})
        
        # Calculate cost per 1M tokens
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_session_summary(self, session_id: str) -> Optional[SessionCostSummary]:
        """Get cost summary for a session"""
        return self._session_costs.get(session_id)
    
    def get_all_sessions(self) -> List[SessionCostSummary]:
        """Get all session summaries"""
        return list(self._session_costs.values())
    
    def check_budget_limit(
        self,
        session_id: str,
        max_cost_usd: float = 1.0
    ) -> tuple[bool, float, str]:
        """
        Check if session has exceeded budget limit
        
        Args:
            session_id: Session identifier
            max_cost_usd: Maximum allowed cost in USD (default: $1.00)
            
        Returns:
            Tuple of (is_over_budget, current_cost, warning_message)
        """
        summary = self.get_session_summary(session_id)
        
        if not summary:
            return (False, 0.0, "")
        
        current_cost = summary.total_cost_usd
        is_over = current_cost >= max_cost_usd
        
        if is_over:
            warning = (
                f"⚠️ Budget limit exceeded! "
                f"Current: ${current_cost:.4f} (฿{current_cost*35:.2f}), "
                f"Limit: ${max_cost_usd:.4f} (฿{max_cost_usd*35:.2f})"
            )
            logger.warning(
                f"[COST] Budget limit exceeded for session {session_id}",
                extra={"session_id": session_id, "current_cost": current_cost, "limit": max_cost_usd}
            )
        else:
            percentage = (current_cost / max_cost_usd) * 100
            warning = (
                f"Budget: ${current_cost:.4f} / ${max_cost_usd:.4f} "
                f"({percentage:.1f}%)"
            )
        
        return (is_over, current_cost, warning)
    
    def reset_session(self, session_id: str):
        """Reset cost tracking for a session"""
        if session_id in self._session_costs:
            del self._session_costs[session_id]
            logger.info(f"[COST] Reset cost tracking for session {session_id}")
    
    def export_to_dict(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export cost data to dictionary
        
        Args:
            session_id: Optional session ID to export single session
            
        Returns:
            Dictionary with cost data
        """
        if session_id:
            summary = self.get_session_summary(session_id)
            if summary:
                return summary.to_dict()
            return {}
        
        # Export all sessions
        return {
            "total_sessions": len(self._session_costs),
            "total_cost_usd": sum(s.total_cost_usd for s in self._session_costs.values()),
            "total_calls": sum(s.total_calls for s in self._session_costs.values()),
            "total_tokens": sum(s.total_tokens for s in self._session_costs.values()),
            "sessions": [s.to_dict() for s in self._session_costs.values()]
        }
    
    def get_cost_by_brain_type(self, session_id: str) -> Dict[str, float]:
        """Get cost breakdown by brain type"""
        summary = self.get_session_summary(session_id)
        if not summary:
            return {}
        
        breakdown = {}
        for call in summary.calls:
            brain_type = call.brain_type
            if brain_type not in breakdown:
                breakdown[brain_type] = 0.0
            breakdown[brain_type] += call.estimated_cost_usd
        
        return breakdown


# Global cost tracker instance
cost_tracker = CostTracker()
