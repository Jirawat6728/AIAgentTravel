"""
โมดูลการทำให้ข้อมูลเป็นมาตรฐาน (Data Normalization)
ปรับค่าของแต่ละปัจจัยให้อยู่ในช่วงมาตรฐานเดียวกัน (0–1) ก่อนนำไปคำนวณคะแนน
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union

from app.core.logging import get_logger

logger = get_logger(__name__)


class DataNormalizer:
    """
    Data Normalization using Min-Max Normalization
    
    สมการ: x_ij' = (x_ij - min(x_j)) / (max(x_j) - min(x_j)) (2)
    
    โดยที่:
    - x_ij' = ค่าที่ถูกปรับให้อยู่ในช่วงมาตรฐานของเกณฑ์ j
    - max(x_j) = ค่าสูงสุดของเกณฑ์ j
    - min(x_j) = ค่าต่ำสุดของเกณฑ์ j
    
    เทคนิคนี้ช่วยให้ข้อมูลที่มีหน่วยต่างกัน (เช่น บาท, คะแนนรีวิว, ระยะทาง)
    สามารถเปรียบเทียบกันได้อย่างยุติธรรม
    """
    
    @staticmethod
    def normalize_value(
        value: Union[int, float],
        min_value: Union[int, float],
        max_value: Union[int, float]
    ) -> float:
        """
        Normalize a single value using Min-Max normalization
        
        Args:
            value: ค่าที่ต้องการ normalize (x_ij)
            min_value: ค่าต่ำสุด (min(x_j))
            max_value: ค่าสูงสุด (max(x_j))
            
        Returns:
            Normalized value (x_ij') in range [0, 1]
        """
        if max_value == min_value:
            # Avoid division by zero - return 0.5 as neutral value
            return 0.5
        
        normalized = (value - min_value) / (max_value - min_value)
        
        # Clamp to [0, 1] range
        return max(0.0, min(1.0, normalized))
    
    @staticmethod
    def normalize_list(
        values: List[Union[int, float]],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> List[float]:
        """
        Normalize a list of values using Min-Max normalization
        
        Args:
            values: List of values to normalize
            min_value: Optional minimum (if None, calculated from values)
            max_value: Optional maximum (if None, calculated from values)
            
        Returns:
            List of normalized values in range [0, 1]
        """
        if not values:
            return []
        
        # Calculate min/max if not provided
        if min_value is None:
            min_value = min(values)
        if max_value is None:
            max_value = max(values)
        
        return [
            DataNormalizer.normalize_value(v, min_value, max_value)
            for v in values
        ]
    
    @staticmethod
    def normalize_criteria(
        data: List[Dict[str, Any]],
        criteria: List[str],
        inverse: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, float]]:
        """
        Normalize multiple criteria across multiple data points
        
        Args:
            data: List of data dictionaries (each represents one option)
            criteria: List of criteria keys to normalize (e.g., ["price", "rating", "distance"])
            inverse: Dict mapping criteria to inverse flag (True = lower is better, e.g., price)
            
        Returns:
            List of normalized data dictionaries
        """
        if not data or not criteria:
            return []
        
        inverse = inverse or {}
        
        # Extract values for each criterion
        criterion_values: Dict[str, List[float]] = {}
        for criterion in criteria:
            values = []
            for item in data:
                value = item.get(criterion)
                if value is not None:
                    try:
                        values.append(float(value))
                    except (ValueError, TypeError):
                        pass
            
            if values:
                criterion_values[criterion] = values
        
        # Normalize each criterion
        normalized_data = []
        for item in data:
            normalized_item = {}
            
            for criterion in criteria:
                if criterion not in criterion_values:
                    normalized_item[criterion] = 0.5  # Default neutral value
                    continue
                
                value = item.get(criterion)
                if value is None:
                    normalized_item[criterion] = 0.5  # Default neutral value
                    continue
                
                try:
                    value_float = float(value)
                    min_val = min(criterion_values[criterion])
                    max_val = max(criterion_values[criterion])
                    
                    normalized = DataNormalizer.normalize_value(value_float, min_val, max_val)
                    
                    # Apply inverse if needed (for criteria where lower is better)
                    if inverse.get(criterion, False):
                        normalized = 1.0 - normalized
                    
                    normalized_item[criterion] = normalized
                except (ValueError, TypeError):
                    normalized_item[criterion] = 0.5  # Default neutral value
            
            normalized_data.append(normalized_item)
        
        return normalized_data
    
    @staticmethod
    def normalize_option_scores(
        options: List[Dict[str, Any]],
        criteria_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Normalize option scores for fair comparison
        
        This is specifically designed for travel options (flights, hotels, etc.)
        where different criteria have different units (THB, stars, minutes, km)
        
        Args:
            options: List of option dictionaries
            criteria_weights: Optional weights for each criterion (default: equal weights)
            
        Returns:
            List of options with normalized scores
        """
        if not options:
            return []
        
        # Define criteria to normalize
        # Price: inverse (lower is better)
        # Rating: normal (higher is better)
        # Duration: inverse (lower is better)
        # Distance: inverse (lower is better)
        # Review count: normal (higher is better)
        
        criteria = []
        inverse_map = {}
        
        # Check which criteria exist in options
        sample_option = options[0]
        
        if "price_amount" in sample_option or "price_total" in sample_option or "price" in sample_option:
            criteria.append("price")
            inverse_map["price"] = True
        
        if "rating" in sample_option or "stars" in sample_option:
            criteria.append("rating")
            inverse_map["rating"] = False
        
        if "duration" in sample_option or "duration_minutes" in sample_option:
            criteria.append("duration")
            inverse_map["duration"] = True
        
        if "distance" in sample_option or "distance_km" in sample_option:
            criteria.append("distance")
            inverse_map["distance"] = True
        
        if "review_count" in sample_option or "reviews_count" in sample_option:
            criteria.append("review_count")
            inverse_map["review_count"] = False
        
        if not criteria:
            logger.warning("No criteria found to normalize")
            return options
        
        # Normalize criteria
        normalized_scores = DataNormalizer.normalize_criteria(
            options,
            criteria,
            inverse_map
        )
        
        # Add normalized scores to options
        result = []
        for i, option in enumerate(options):
            normalized_option = {**option}
            normalized_option["_normalized_scores"] = normalized_scores[i]
            result.append(normalized_option)
        
        logger.info(
            f"Normalized {len(options)} options with criteria: {criteria}"
        )
        
        return result


# Global normalizer instance
_normalizer = DataNormalizer()

def normalize_options(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to normalize options"""
    return _normalizer.normalize_option_scores(options)
