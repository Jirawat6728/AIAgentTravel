"""
แพตเทิร์นความทนทานต่อข้อผิดพลาด (Resilience)
รวม Circuit Breaker การจำกัดอัตรา Retry และการตรวจสอบสุขภาพระบบ
"""

import asyncio
import time
from enum import Enum
from datetime import datetime
from collections import defaultdict
from typing import Callable, Any, Optional, Dict, Tuple
from app.core.logging import get_logger
from app.storage.connection_manager import MongoConnectionManager, RedisConnectionManager

logger = get_logger(__name__)


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker to prevent cascading failures
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result from function
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check if we should attempt recovery
            if self.state == CircuitState.OPEN:
                if self.last_failure_time:
                    time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                    if time_since_failure >= self.recovery_timeout:
                        logger.info(f"Circuit breaker attempting recovery for {func.__name__}")
                        self.state = CircuitState.HALF_OPEN
                        self.failure_count = 0
                    else:
                        raise Exception(
                            f"Circuit breaker is OPEN. Service unavailable. "
                            f"Retry after {self.recovery_timeout - int(time_since_failure)} seconds"
                        )
                else:
                    raise Exception("Circuit breaker is OPEN. Service unavailable.")
        
        # Attempt to call the function
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success - reset circuit if it was half-open
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    logger.info(f"Circuit breaker recovered for {func.__name__}")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                elif self.state == CircuitState.CLOSED:
                    self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = datetime.now()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.error(
                        f"Circuit breaker OPENED for {func.__name__} "
                        f"after {self.failure_count} failures"
                    )
                
            raise
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker manually reset")


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window
    Kept for backward compatibility and as fallback
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = False  # Simple lock flag
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed
        
        Args:
            identifier: Unique identifier (e.g., IP address, user_id)
            
        Returns:
            (is_allowed, remaining_requests)
        """
        current_time = time.time()
        
        # Clean old requests outside window
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if current_time - req_time < self.window_seconds
            ]
        
        # Check if limit exceeded
        request_count = len(self.requests[identifier])
        
        if request_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}: {request_count}/{self.max_requests}")
            return False, 0
        
        # Add current request
        self.requests[identifier].append(current_time)
        
        remaining = self.max_requests - len(self.requests[identifier])
        return True, remaining
    
    async def is_allowed_async(self, identifier: str) -> Tuple[bool, int]:
        """Async wrapper for is_allowed (for compatibility with RedisRateLimiter)"""
        return self.is_allowed(identifier)
    
    def reset(self, identifier: str = None):
        """Reset rate limit for identifier or all"""
        if identifier:
            self.requests.pop(identifier, None)
        else:
            self.requests.clear()
    
    async def reset_async(self, identifier: str = None):
        """Async wrapper for reset (for compatibility with RedisRateLimiter)"""
        self.reset(identifier)


# =============================================================================
# Retry Logic with Exponential Backoff
# =============================================================================

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    *args,
    **kwargs
) -> Any:
    """
    Retry function with exponential backoff
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Result from function
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * exponential_base, max_delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                raise
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


# =============================================================================
# Global Instances
# =============================================================================

# Circuit Breakers
omise_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

llm_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception
)

amadeus_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

# Rate Limiters - Use Redis-based rate limiting with memory fallback
try:
    from app.core.redis_rate_limiter import RedisRateLimiter
    # Use Redis for distributed rate limiting (falls back to memory if Redis unavailable)
    chat_rate_limiter = RedisRateLimiter(max_requests=30, window_seconds=60, fallback_to_memory=True)
    api_rate_limiter = RedisRateLimiter(max_requests=100, window_seconds=60, fallback_to_memory=True)
    payment_rate_limiter = RedisRateLimiter(max_requests=10, window_seconds=60, fallback_to_memory=True)
    logger.info("Using Redis-based rate limiting (with memory fallback)")
except Exception as e:
    logger.warning(f"Failed to initialize Redis rate limiters, using in-memory: {e}")
    # Fallback to in-memory rate limiters
    chat_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 30 requests per minute
    api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 requests per minute
    payment_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 payment attempts per minute


# =============================================================================
# Health Monitoring and Crash Recovery (from crash_recovery.py)
# =============================================================================

class HealthMonitor:
    """Monitor backend health and trigger recovery actions"""
    
    def __init__(self, check_interval: int = 30):
        """
        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self.is_running = False
        self.last_check = None
        self.health_status = {
            "mongodb": False,
            "redis": False,
            "last_check": None
        }
        self.recovery_callbacks: list[Callable] = []
    
    def register_recovery_callback(self, callback: Callable):
        """Register a callback to be called when recovery is needed"""
        self.recovery_callbacks.append(callback)
    
    async def check_health(self) -> dict:
        """Check health of all services"""
        status = {
            "mongodb": False,
            "redis": False,
            "timestamp": time.time()
        }
        
        # Check MongoDB
        try:
            mongo_mgr = MongoConnectionManager.get_instance()
            if await mongo_mgr.mongo_ping():
                status["mongodb"] = True
        except Exception as e:
            logger.warning(f"MongoDB health check failed: {e}")
            status["mongodb"] = False
        
        # Check Redis (optional - don't log warnings if unavailable)
        try:
            redis_mgr = RedisConnectionManager.get_instance()
            redis_client = await redis_mgr.get_redis()
            if redis_client:
                await asyncio.wait_for(redis_client.ping(), timeout=0.5)
                status["redis"] = True
            else:
                status["redis"] = False
        except Exception as e:
            # Only log if Redis was previously available (to detect new failures)
            if status.get("redis", False):
                logger.warning(f"Redis health check failed: {e}")
            status["redis"] = False
        
        self.health_status = status
        self.last_check = time.time()
        
        return status
    
    async def trigger_recovery(self, service: str):
        """Trigger recovery for a failed service"""
        logger.warning(f"Triggering recovery for {service}")
        
        for callback in self.recovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(service)
                else:
                    callback(service)
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")
    
    async def start_monitoring(self):
        """Start health monitoring loop"""
        if self.is_running:
            logger.warning("Health monitor already running")
            return
        
        self.is_running = True
        logger.info(f"Health monitor started (check interval: {self.check_interval}s)")
        
        consecutive_failures = {
            "mongodb": 0,
            "redis": 0
        }
        
        while self.is_running:
            try:
                status = await self.check_health()
                
                # Check MongoDB
                if not status["mongodb"]:
                    consecutive_failures["mongodb"] += 1
                    if consecutive_failures["mongodb"] >= 3:
                        logger.error("MongoDB has been unhealthy for 3 consecutive checks")
                        await self.trigger_recovery("mongodb")
                else:
                    consecutive_failures["mongodb"] = 0
                
                # Check Redis (optional - only recover if it was previously working)
                if not status["redis"]:
                    # Only attempt recovery if Redis was working before
                    # Don't spam recovery attempts if Redis is intentionally disabled
                    if status.get("redis_was_available", False):
                        consecutive_failures["redis"] += 1
                        if consecutive_failures["redis"] >= 3:
                            logger.warning("Redis has been unhealthy for 3 consecutive checks")
                            await self.trigger_recovery("redis")
                else:
                    consecutive_failures["redis"] = 0
                    status["redis_was_available"] = True
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_running = False
        logger.info("Health monitor stopped")


# Global health monitor instance
health_monitor = HealthMonitor(check_interval=30)


async def recover_mongodb():
    """Recover MongoDB connection"""
    try:
        logger.info("Attempting MongoDB recovery...")
        mongo_mgr = MongoConnectionManager.get_instance()
        
        # Force reinitialize connection
        mongo_mgr._mongo_client = None
        mongo_mgr._mongo_db = None
        
        # Try to reconnect
        db = mongo_mgr.get_mongo_database()
        await db.command('ping')
        
        logger.info("MongoDB recovery successful")
        return True
    except Exception as e:
        logger.error(f"MongoDB recovery failed: {e}")
        return False


async def recover_redis():
    """Recover Redis connection (only if Redis was previously available)"""
    try:
        logger.info("Attempting Redis recovery...")
        redis_mgr = RedisConnectionManager.get_instance()
        
        # Force reinitialize connection
        if hasattr(redis_mgr, '_redis_unavailable'):
            redis_mgr._redis_unavailable = False
        redis_mgr._redis_client = None
        
        # Try to reconnect
        redis_client = await redis_mgr.get_redis()
        if redis_client:
            await redis_client.ping()
            logger.info("Redis recovery successful")
            return True
        else:
            logger.debug("Redis recovery skipped - service not available")
            return False
    except Exception as e:
        logger.debug(f"Redis recovery failed: {e}")
        return False


# Register recovery callbacks (only MongoDB is critical)
health_monitor.register_recovery_callback(recover_mongodb)
# Redis recovery is optional - only register if needed
# health_monitor.register_recovery_callback(recover_redis)
