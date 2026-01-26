"""
Model Selector Service
Auto-selects optimal Gemini model based on task complexity
"""

from typing import Optional, Literal
from enum import Enum
import re

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"       # Simple queries, confirmations, basic info
    MODERATE = "moderate"   # Standard planning, search, recommendations
    COMPLEX = "complex"     # Complex reasoning, multi-step planning, edge cases


class ModelTier(str, Enum):
    """Gemini model tiers"""
    FLASH = "flash"   # Fast, cost-effective (gemini-2.5-flash)
    PRO = "pro"       # Balanced performance (gemini-2.5-pro)
    ULTRA = "ultra"   # Maximum capability (gemini-2.5-pro)


class ModelSelector:
    """
    Intelligent model selector that analyzes task complexity
    and recommends the optimal Gemini model tier
    """
    
    # Complexity indicators
    COMPLEX_KEYWORDS = [
        "multi-city", "complex", "detailed", "comprehensive", "analyze", "compare",
        "optimize", "recommend", "plan trip", "multiple", "batch", "all segments",
        "ทริปซับซ้อน", "วางแผน", "เปรียบเทียบ", "วิเคราะห์", "หลายเมือง"
    ]
    
    MODERATE_KEYWORDS = [
        "search", "find", "book", "update", "change", "modify", "add", "remove",
        "ค้นหา", "จอง", "เปลี่ยน", "แก้ไข", "เพิ่ม", "ลบ"
    ]
    
    SIMPLE_KEYWORDS = [
        "yes", "no", "ok", "confirm", "cancel", "help", "hello", "hi",
        "ใช่", "ไม่", "ตกลง", "ยืนยัน", "ยกเลิก", "สวัสดี"
    ]
    
    @classmethod
    def analyze_complexity(
        cls,
        user_input: str,
        context: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> TaskComplexity:
        """
        Analyze task complexity based on user input and context
        
        Args:
            user_input: User's message
            context: Optional context (e.g., "controller", "responder", "memory")
            task_type: Optional task type hint
            
        Returns:
            TaskComplexity level
        """
        if not user_input or len(user_input.strip()) == 0:
            return TaskComplexity.SIMPLE
        
        # Normalize input
        text = user_input.lower().strip()
        
        # 1. Length-based heuristic (longer = potentially more complex)
        if len(text) > 200:
            complexity_score = 2  # Start with moderate
        elif len(text) > 100:
            complexity_score = 1
        else:
            complexity_score = 0
        
        # 2. Keyword-based analysis
        complex_count = sum(1 for keyword in cls.COMPLEX_KEYWORDS if keyword.lower() in text)
        moderate_count = sum(1 for keyword in cls.MODERATE_KEYWORDS if keyword.lower() in text)
        simple_count = sum(1 for keyword in cls.SIMPLE_KEYWORDS if keyword.lower() in text)
        
        # Update score based on keywords
        if complex_count > 0:
            complexity_score += 2
        elif moderate_count > 0:
            complexity_score += 1
        elif simple_count > 0:
            complexity_score -= 1
        
        # 3. Special patterns
        # Multiple dates or locations indicate complexity
        date_pattern = r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}|\d{1,2}\s+\w+'
        dates_found = len(re.findall(date_pattern, text))
        if dates_found > 2:
            complexity_score += 1
        
        # Multiple "and" or "," suggests multiple requests
        if text.count(" and ") > 1 or text.count(",") > 2 or text.count(" และ ") > 1:
            complexity_score += 1
        
        # 4. Context-based adjustment
        if context == "controller":
            # Controller decisions can be complex
            if task_type in ["CREATE_ITINERARY", "BATCH", "CALL_SEARCH"]:
                complexity_score += 1
        elif context == "memory":
            # Memory consolidation is usually simple
            complexity_score = max(0, complexity_score - 1)
        
        # 5. Final classification
        if complexity_score >= 3:
            return TaskComplexity.COMPLEX
        elif complexity_score >= 1:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE
    
    @classmethod
    def select_model(cls, complexity: TaskComplexity) -> ModelTier:
        """
        Select optimal model tier based on complexity
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Recommended model tier
        """
        if complexity == TaskComplexity.COMPLEX:
            return ModelTier.PRO  # Use Pro for complex tasks
        elif complexity == TaskComplexity.MODERATE:
            return ModelTier.FLASH  # Flash is sufficient for moderate tasks
        else:
            return ModelTier.FLASH  # Flash for simple tasks (fast & cheap)
    
    @classmethod
    def get_model_name(cls, tier: ModelTier) -> str:
        """
        Get actual Gemini model name for a tier
        
        Args:
            tier: Model tier
            
        Returns:
            Gemini model name
        """
        if tier == ModelTier.FLASH:
            return settings.gemini_flash_model
        elif tier == ModelTier.PRO:
            return settings.gemini_pro_model
        elif tier == ModelTier.ULTRA:
            return settings.gemini_ultra_model
        else:
            return settings.gemini_model_name  # Fallback
    
    @classmethod
    def recommend_model(
        cls,
        user_input: str,
        context: Optional[str] = None,
        task_type: Optional[str] = None,
        force_tier: Optional[ModelTier] = None
    ) -> tuple[str, TaskComplexity]:
        """
        Main recommendation method
        
        Args:
            user_input: User's message
            context: Optional context
            task_type: Optional task type
            force_tier: Force a specific tier (override auto-selection)
            
        Returns:
            Tuple of (model_name, complexity)
        """
        # Check if auto-switching is enabled
        if not settings.enable_auto_model_switching:
            logger.debug("Auto model switching disabled, using default model")
            return settings.gemini_model_name, TaskComplexity.MODERATE
        
        # Analyze complexity
        complexity = cls.analyze_complexity(user_input, context, task_type)
        
        # Select tier (or use forced tier)
        if force_tier:
            tier = force_tier
            logger.info(f"Model tier forced: {tier}")
        else:
            tier = cls.select_model(complexity)
        
        # Get model name
        model_name = cls.get_model_name(tier)
        
        logger.info(f"Model selection: {model_name} (complexity={complexity.value}, tier={tier.value})")
        
        return model_name, complexity


# Convenience function
def select_model_for_task(
    user_input: str,
    context: Optional[str] = None,
    task_type: Optional[str] = None
) -> str:
    """
    Quick helper to get model name for a task
    
    Args:
        user_input: User's message
        context: Optional context
        task_type: Optional task type
        
    Returns:
        Recommended Gemini model name
    """
    model_name, _ = ModelSelector.recommend_model(user_input, context, task_type)
    return model_name
