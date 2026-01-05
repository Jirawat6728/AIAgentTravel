"""
Validation functions for dates, locations, numbers
Used to improve accuracy and prevent errors
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple
import re

from utils.thai_date import parse_thai_date_nearest_future


def validate_date(date_str: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and normalize date string.
    
    Returns:
        (is_valid, normalized_date, error_message)
        - is_valid: True if date is valid
        - normalized_date: ISO format date (YYYY-MM-DD) or None
        - error_message: Error message if invalid, None if valid
    """
    if not date_str:
        return False, None, "Date is empty"
    
    if not isinstance(date_str, str):
        date_str = str(date_str)
    
    date_str = date_str.strip()
    
    # Try ISO format first (YYYY-MM-DD)
    iso_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if re.match(iso_pattern, date_str):
        try:
            parsed_date = date.fromisoformat(date_str)
            # Check if date is in the past (more than 1 day ago)
            today = date.today()
            if parsed_date < today - timedelta(days=1):
                return False, None, f"Date {date_str} is in the past"
            return True, date_str, None
        except ValueError:
            return False, None, f"Invalid ISO date format: {date_str}"
    
    # Try Thai date parsing
    try:
        parsed_date = parse_thai_date_nearest_future(date_str)
        if parsed_date:
            iso_date = parsed_date.isoformat()
            today = date.today()
            if parsed_date < today - timedelta(days=1):
                return False, None, f"Date {date_str} is in the past"
            return True, iso_date, None
        else:
            return False, None, f"Could not parse date: {date_str}"
    except Exception as e:
        return False, None, f"Error parsing date: {str(e)}"


def validate_location(location: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate location string.
    
    Returns:
        (is_valid, normalized_location, error_message)
        - is_valid: True if location looks valid
        - normalized_location: Normalized location string or None
        - error_message: Error message if invalid, None if valid
    """
    if not location:
        return False, None, "Location is empty"
    
    if not isinstance(location, str):
        location = str(location)
    
    location = location.strip()
    
    # Basic validation: should have at least 2 characters
    if len(location) < 2:
        return False, None, f"Location too short: {location}"
    
    # Should not contain only numbers
    if location.isdigit():
        return False, None, f"Location cannot be only numbers: {location}"
    
    # Normalize: remove extra spaces, capitalize first letter
    normalized = re.sub(r'\s+', ' ', location).strip()
    
    # Common invalid patterns
    invalid_patterns = [
        r'^[^a-zA-Zก-๙]',  # Starts with non-letter
        r'^\d+$',  # Only numbers
        r'^[^\w\sก-๙]+$',  # Only special characters
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, normalized):
            return False, None, f"Invalid location format: {location}"
    
    return True, normalized, None


def validate_number(
    value: Any,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    allow_zero: bool = True,
    value_type: str = "integer"  # "integer" or "float"
) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate and normalize number.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        allow_zero: Whether zero is allowed
        value_type: "integer" or "float"
    
    Returns:
        (is_valid, normalized_value, error_message)
        - is_valid: True if number is valid
        - normalized_value: Float value or None
        - error_message: Error message if invalid, None if valid
    """
    if value is None:
        return False, None, "Number is None"
    
    # Convert to string first to handle various formats
    if isinstance(value, str):
        value_str = value.strip()
        # Remove common separators (commas, spaces)
        value_str = re.sub(r'[,\s]', '', value_str)
    else:
        value_str = str(value)
    
    try:
        if value_type == "integer":
            num_value = int(float(value_str))  # Convert via float first to handle "1.0"
        else:
            num_value = float(value_str)
    except (ValueError, TypeError):
        return False, None, f"Invalid number format: {value}"
    
    # Check zero
    if not allow_zero and num_value == 0:
        return False, None, "Zero is not allowed"
    
    # Check minimum
    if min_val is not None and num_value < min_val:
        return False, None, f"Number {num_value} is less than minimum {min_val}"
    
    # Check maximum
    if max_val is not None and num_value > max_val:
        return False, None, f"Number {num_value} is greater than maximum {max_val}"
    
    return True, num_value, None


def validate_travelers(adults: Any, children: Any = None) -> Tuple[bool, Dict[str, int], Optional[str]]:
    """
    Validate travelers count (adults and children).
    
    Returns:
        (is_valid, normalized_values, error_message)
        - is_valid: True if valid
        - normalized_values: {"adults": int, "children": int}
        - error_message: Error message if invalid, None if valid
    """
    # Validate adults
    adults_valid, adults_val, adults_error = validate_number(
        adults,
        min_val=1,
        max_val=20,
        allow_zero=False,
        value_type="integer"
    )
    
    if not adults_valid:
        return False, {}, f"Invalid adults count: {adults_error}"
    
    # Validate children (optional)
    children_val = 0
    if children is not None and children != "":
        children_valid, children_val, children_error = validate_number(
            children,
            min_val=0,
            max_val=20,
            allow_zero=True,
            value_type="integer"
        )
        
        if not children_valid:
            return False, {}, f"Invalid children count: {children_error}"
    
    # Check total travelers
    total = adults_val + children_val
    if total > 20:
        return False, {}, f"Total travelers ({total}) exceeds maximum (20)"
    
    return True, {"adults": adults_val, "children": children_val}, None


def validate_travel_slots(slots: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validate travel slots and return normalized values with errors.
    
    Returns:
        (is_valid, normalized_slots, error_messages)
        - is_valid: True if all required fields are valid
        - normalized_slots: Slots with validated/normalized values
        - error_messages: List of error messages
    """
    normalized = {}
    errors = []
    
    # Validate origin
    if slots.get("origin"):
        origin_valid, origin_val, origin_error = validate_location(slots["origin"])
        if origin_valid:
            normalized["origin"] = origin_val
        else:
            errors.append(f"Origin: {origin_error}")
    
    # Validate destination
    if slots.get("destination"):
        dest_valid, dest_val, dest_error = validate_location(slots["destination"])
        if dest_valid:
            normalized["destination"] = dest_val
        else:
            errors.append(f"Destination: {dest_error}")
    
    # Validate start_date
    if slots.get("start_date"):
        date_valid, date_val, date_error = validate_date(slots["start_date"])
        if date_valid:
            normalized["start_date"] = date_val
        else:
            errors.append(f"Start date: {date_error}")
    
    # Validate travelers
    if slots.get("adults") is not None:
        travelers_valid, travelers_val, travelers_error = validate_travelers(
            slots.get("adults"),
            slots.get("children")
        )
        if travelers_valid:
            normalized["adults"] = travelers_val["adults"]
            normalized["children"] = travelers_val["children"]
        else:
            errors.append(f"Travelers: {travelers_error}")
    
    # Validate nights/days
    if slots.get("nights") is not None:
        nights_valid, nights_val, nights_error = validate_number(
            slots["nights"],
            min_val=0,
            max_val=365,
            allow_zero=True,
            value_type="integer"
        )
        if nights_valid:
            normalized["nights"] = int(nights_val)
        else:
            errors.append(f"Nights: {nights_error}")
    
    if slots.get("days") is not None:
        days_valid, days_val, days_error = validate_number(
            slots["days"],
            min_val=1,
            max_val=366,
            allow_zero=False,
            value_type="integer"
        )
        if days_valid:
            normalized["days"] = int(days_val)
        else:
            errors.append(f"Days: {days_error}")
    
    # Copy other fields that don't need validation
    for key, value in slots.items():
        if key not in normalized and key not in ["origin", "destination", "start_date", "adults", "children", "nights", "days"]:
            normalized[key] = value
    
    is_valid = len(errors) == 0
    return is_valid, normalized, errors

