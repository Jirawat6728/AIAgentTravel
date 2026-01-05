from __future__ import annotations

import re
from typing import Dict, Any, List


def parse_segment_actions(user_message: str) -> Dict[str, Any]:
    """
    Parse user message to extract segment edit/delete actions.
    
    Examples:
    - "แก้ไขที่พัก 1" → {"edit": [0], "delete": []}  # 0-based index
    - "ลบที่พัก 2 และ 3" → {"edit": [], "delete": [1, 2]}
    - "แก้ไขที่พัก 1 ลบที่พัก 2 และ 3" → {"edit": [0], "delete": [1, 2]}
    - "แก้ไขไฟลต์ 1" → {"edit": [0], "delete": []}
    - "ลบไฟลต์ 2" → {"edit": [], "delete": [1]}
    """
    actions = {
        "edit": [],
        "delete": [],
    }
    
    # Patterns for hotel (Thai and English)
    hotel_edit_patterns = [
        r'แก้ไขที่พัก\s*(\d+)',
        r'แก้ที่พัก\s*(\d+)',
        r'แก้ไขโรงแรม\s*(\d+)',
        r'แก้โรงแรม\s*(\d+)',
        r'edit\s+hotel\s*(\d+)',
    ]
    
    hotel_delete_patterns = [
        r'ลบที่พัก\s*(\d+)',
        r'ลบโรงแรม\s*(\d+)',
        r'delete\s+hotel\s*(\d+)',
    ]
    
    # Patterns for flight (Thai and English)
    flight_edit_patterns = [
        r'แก้ไขไฟลต์\s*(\d+)',
        r'แก้ไฟลต์\s*(\d+)',
        r'แก้ไขเที่ยวบิน\s*(\d+)',
        r'แก้เที่ยวบิน\s*(\d+)',
        r'edit\s+flight\s*(\d+)',
    ]
    
    flight_delete_patterns = [
        r'ลบไฟลต์\s*(\d+)',
        r'ลบเที่ยวบิน\s*(\d+)',
        r'delete\s+flight\s*(\d+)',
    ]
    
    # Extract hotel edit actions
    for pattern in hotel_edit_patterns:
        matches = re.finditer(pattern, user_message, re.IGNORECASE)
        for match in matches:
            segment_num = int(match.group(1))
            idx = segment_num - 1  # Convert to 0-based
            if idx not in actions["edit"]:
                actions["edit"].append(idx)
    
    # Extract hotel delete actions
    hotel_delete_matches = []
    for pattern in hotel_delete_patterns:
        matches = re.finditer(pattern, user_message, re.IGNORECASE)
        for match in matches:
            segment_num = int(match.group(1))
            idx = segment_num - 1
            if idx not in hotel_delete_matches:
                hotel_delete_matches.append(idx)
    
    # Handle "และ" pattern for hotel: "ลบที่พัก 2 และ 3"
    hotel_and_pattern = r'ลบที่พัก\s*(\d+)\s*และ\s*(\d+)'
    hotel_and_matches = re.finditer(hotel_and_pattern, user_message, re.IGNORECASE)
    for match in hotel_and_matches:
        idx1 = int(match.group(1)) - 1
        idx2 = int(match.group(2)) - 1
        if idx1 not in hotel_delete_matches:
            hotel_delete_matches.append(idx1)
        if idx2 not in hotel_delete_matches:
            hotel_delete_matches.append(idx2)
    
    # Extract flight edit actions
    for pattern in flight_edit_patterns:
        matches = re.finditer(pattern, user_message, re.IGNORECASE)
        for match in matches:
            segment_num = int(match.group(1))
            idx = segment_num - 1
            if idx not in actions["edit"]:
                actions["edit"].append(idx)
    
    # ✅ Extract add/remove segment actions (for hotel)
    # Patterns: "เพิ่มที่พัก 1 segment", "เพิ่มที่พัก 1", "add hotel 1 segment"
    add_segment_patterns = [
        r'เพิ่มที่พัก\s*(\d+)\s*segment',
        r'เพิ่มที่พัก\s*(\d+)',
        r'เพิ่มโรงแรม\s*(\d+)\s*segment',
        r'เพิ่มโรงแรม\s*(\d+)',
        r'add\s+hotel\s*(\d+)\s*segment',
    ]
    
    for pattern in add_segment_patterns:
        matches = re.finditer(pattern, user_message, re.IGNORECASE)
        for match in matches:
            num_segments = int(match.group(1))
            actions["add"] = max(actions["add"], num_segments)  # Take maximum if multiple mentions
    
    # Patterns: "ลดที่พัก 1 segment", "ลดที่พัก 1", "remove hotel 1 segment"
    remove_segment_patterns = [
        r'ลดที่พัก\s*(\d+)\s*segment',
        r'ลดที่พัก\s*(\d+)',
        r'ลดโรงแรม\s*(\d+)\s*segment',
        r'ลดโรงแรม\s*(\d+)',
        r'remove\s+hotel\s*(\d+)\s*segment',
    ]
    
    # Note: "ลด" (reduce) is treated as delete from the end
    # We'll handle this in the orchestrator by deleting the last N segments
    
    # Extract flight delete actions
    flight_delete_matches = []
    for pattern in flight_delete_patterns:
        matches = re.finditer(pattern, user_message, re.IGNORECASE)
        for match in matches:
            segment_num = int(match.group(1))
            idx = segment_num - 1
            if idx not in flight_delete_matches:
                flight_delete_matches.append(idx)
    
    # Handle "และ" pattern for flight: "ลบไฟลต์ 2 และ 3"
    flight_and_pattern = r'ลบไฟลต์\s*(\d+)\s*และ\s*(\d+)'
    flight_and_matches = re.finditer(flight_and_pattern, user_message, re.IGNORECASE)
    for match in flight_and_matches:
        idx1 = int(match.group(1)) - 1
        idx2 = int(match.group(2)) - 1
        if idx1 not in flight_delete_matches:
            flight_delete_matches.append(idx1)
        if idx2 not in flight_delete_matches:
            flight_delete_matches.append(idx2)
    
    # Combine all delete actions
    actions["delete"] = sorted(list(set(hotel_delete_matches + flight_delete_matches)))
    actions["edit"] = sorted(list(set(actions["edit"])))
    
    return actions

