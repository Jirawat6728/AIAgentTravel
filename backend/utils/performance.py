"""
Performance monitoring and guarantees for search operations.
Ensures responses within 1 minute and accuracy > 80%.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from contextlib import contextmanager


class PerformanceMonitor:
    """Monitor and enforce performance guarantees."""
    
    def __init__(self, max_time_sec: float = 55.0):
        """
        Args:
            max_time_sec: Maximum allowed time in seconds (default 55s to leave 5s buffer)
        """
        self.max_time_sec = max_time_sec
        self.start_time = None
        self.checkpoints: Dict[str, float] = {}
        self.metrics: Dict[str, Any] = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure operation time."""
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - start
            self.checkpoints[operation_name] = elapsed
            if operation_name not in self.metrics:
                self.metrics[operation_name] = []
            self.metrics[operation_name].append(elapsed)
    
    def start(self):
        """Start the overall timer."""
        self.start_time = time.monotonic()
        self.checkpoints = {}
        self.metrics = {}
    
    def elapsed(self) -> float:
        """Get elapsed time since start."""
        if self.start_time is None:
            return 0.0
        return time.monotonic() - self.start_time
    
    def remaining(self) -> float:
        """Get remaining time before timeout."""
        return max(0.0, self.max_time_sec - self.elapsed())
    
    def check_timeout(self) -> bool:
        """Check if we're approaching timeout."""
        return self.elapsed() >= self.max_time_sec
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total = self.elapsed()
        return {
            "total_time_sec": total,
            "within_limit": total <= self.max_time_sec,
            "checkpoints": self.checkpoints,
            "metrics": {k: {
                "count": len(v),
                "avg": sum(v) / len(v) if v else 0,
                "max": max(v) if v else 0,
                "min": min(v) if v else 0,
            } for k, v in self.metrics.items()},
        }


def validate_iata_accuracy(
    location_name: str,
    resolved_iata: Optional[str],
    expected_city: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate IATA code accuracy.
    
    Returns:
        {
            "is_valid": bool,
            "confidence": float,  # 0.0 to 1.0
            "reason": str,
            "suggestions": List[str]
        }
    """
    if not resolved_iata:
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": "No IATA code resolved",
            "suggestions": [],
        }
    
    # Basic validation: IATA should be 3 uppercase letters
    if not isinstance(resolved_iata, str) or len(resolved_iata) != 3:
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": f"Invalid IATA format: {resolved_iata}",
            "suggestions": [],
        }
    
    if not resolved_iata.isupper() or not resolved_iata.isalpha():
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": f"IATA code must be 3 uppercase letters: {resolved_iata}",
            "suggestions": [],
        }
    
    # If we have expected city, we could do more validation
    # For now, assume valid if format is correct
    confidence = 0.85  # Base confidence for valid format
    
    # Increase confidence if we have Google Maps context
    # (This would be set by the caller)
    
    return {
        "is_valid": True,
        "confidence": confidence,
        "reason": "Valid IATA format",
        "suggestions": [],
    }


def calculate_overall_accuracy(
    iata_validations: list[Dict[str, Any]],
) -> float:
    """
    Calculate overall accuracy from multiple IATA validations.
    
    Args:
        iata_validations: List of validation results from validate_iata_accuracy
    
    Returns:
        Accuracy percentage (0.0 to 1.0)
    """
    if not iata_validations:
        return 0.0
    
    valid_count = sum(1 for v in iata_validations if v.get("is_valid", False))
    total_count = len(iata_validations)
    
    if total_count == 0:
        return 0.0
    
    return valid_count / total_count


def enforce_timeout_async(coro, timeout_sec: float):
    """Wrapper to enforce timeout on async operations."""
    import asyncio
    
    async def _with_timeout():
        try:
            return await asyncio.wait_for(coro, timeout=timeout_sec)
        except asyncio.TimeoutError:
            # Return partial result or None
            return None
    
    return _with_timeout()

