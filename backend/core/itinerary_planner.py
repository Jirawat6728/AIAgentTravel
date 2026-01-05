"""
Itinerary Planner - Uses LLM + Google Maps to create Day-by-Day Route plans.
Works like a puzzle game: LLM analyzes user input, creates route structure,
then uses Google Maps to get actual routes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import date, timedelta

from services.gemini_service import call_gemini
from services.google_maps_service import get_route, geocode_address


@dataclass
class RouteSegment:
    """A single route segment (e.g., A->B, B->C)"""
    id: str  # "segment_1", "segment_2", etc.
    origin: str  # Starting point
    destination: str  # Ending point
    day: int  # Day number (1, 2, 3, ...)
    mode: str  # driving, walking, transit, etc.
    distance_km: Optional[float] = None
    duration_hours: Optional[float] = None
    route_data: Optional[Dict[str, Any]] = None  # Google Maps route data


@dataclass
class DayItinerary:
    """A single day's itinerary"""
    day: int
    date: str  # ISO date
    route_segments: List[RouteSegment]  # Routes for this day
    activities: List[str]  # Activities/attractions
    accommodation_city: Optional[str] = None  # Where to stay this night


@dataclass
class ItineraryPlan:
    """Complete itinerary plan with routes and accommodations"""
    trip_title: str
    start_date: str
    end_date: str
    total_days: int
    days: List[DayItinerary]
    route_segments: List[RouteSegment]  # All route segments across all days
    accommodation_slots: List[Dict[str, Any]]  # Accommodation needs by city/day


class ItineraryPlanner:
    """Plans Day-by-Day Itinerary using LLM + Google Maps"""
    
    @staticmethod
    async def plan_itinerary(
        user_message: str,
        travel_slots: Dict[str, Any],
        existing_context: Optional[Dict[str, Any]] = None
    ) -> ItineraryPlan:
        """
        Main planner: Analyzes user input and creates route structure.
        Returns ItineraryPlan with route segments and accommodation needs.
        """
        # Step 1: Use LLM to analyze and create route structure
        route_structure = await ItineraryPlanner._analyze_route_structure(
            user_message, travel_slots
        )
        
        if not route_structure:
            # Fallback: simple origin->destination
            origin = travel_slots.get("origin") or "Unknown"
            destination = travel_slots.get("destination") or "Unknown"
            route_structure = {
                "segments": [
                    {
                        "id": "segment_1",
                        "origin": origin,
                        "destination": destination,
                        "day": 1,
                        "round_trip": True,  # Include return
                    }
                ],
                "days": [
                    {
                        "day": 1,
                        "activities": [],
                        "accommodation_city": destination,
                    }
                ],
            }
        
        # Step 2: Use Google Maps to get actual routes
        route_segments = []
        for seg_data in route_structure.get("segments", []):
            route_seg = await ItineraryPlanner._get_route_from_maps(seg_data)
            if route_seg:
                route_segments.append(route_seg)
        
        # Step 3: Build DayItinerary objects
        days_data = route_structure.get("days", [])
        days = []
        start_date = travel_slots.get("start_date") or date.today().isoformat()
        
        for day_data in days_data:
            day_num = day_data.get("day", 1)
            day_date = ItineraryPlanner._calculate_date(start_date, day_num - 1)
            
            # Find route segments for this day
            day_segments = [seg for seg in route_segments if seg.day == day_num]
            
            day_itinerary = DayItinerary(
                day=day_num,
                date=day_date,
                route_segments=day_segments,
                activities=day_data.get("activities", []),
                accommodation_city=day_data.get("accommodation_city"),
            )
            days.append(day_itinerary)
        
        # Step 4: Create accommodation slots
        accommodation_slots = ItineraryPlanner._create_accommodation_slots(days)
        
        # Step 5: Build ItineraryPlan
        total_days = travel_slots.get("nights", 0) + 1 or len(days)
        end_date = ItineraryPlanner._calculate_date(start_date, total_days - 1)
        
        return ItineraryPlan(
            trip_title=route_structure.get("trip_title") or travel_slots.get("destination", "Trip"),
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            days=days,
            route_segments=route_segments,
            accommodation_slots=accommodation_slots,
        )
    
    @staticmethod
    async def _analyze_route_structure(
        user_message: str,
        travel_slots: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to analyze user message and create route structure.
        Returns structure with segments and day-by-day plan.
        """
        origin = travel_slots.get("origin") or ""
        destination = travel_slots.get("destination") or ""
        nights = travel_slots.get("nights") or 3
        start_date = travel_slots.get("start_date") or ""
        
        prompt = f"""คุณเป็นผู้เชี่ยวชาญการวางแผนทริป ให้วิเคราะห์ข้อความผู้ใช้และสร้างโครงสร้างเส้นทางการเดินทาง (Day-by-Day Itinerary)

ข้อมูลทริป:
- จุดเริ่มต้น: {origin}
- จุดหมายปลายทาง: {destination}
- จำนวนคืน: {nights} คืน ({nights + 1} วัน)
- วันเริ่มต้น: {start_date}

ข้อความผู้ใช้:
"{user_message}"

ให้วิเคราะห์และสร้างโครงสร้างเส้นทางเป็น JSON ตามรูปแบบนี้:

{{
  "trip_title": "ชื่อทริป",
  "segments": [
    {{
      "id": "segment_1",
      "origin": "จุดเริ่มต้น",
      "destination": "จุดหมาย",
      "day": 1,
      "round_trip": false,
      "description": "คำอธิบายสั้นๆ",
      "activities": ["กิจกรรมที่จุดหมาย"]
    }},
    {{
      "id": "segment_2",
      "origin": "จุดเดิม",
      "destination": "จุดต่อไป",
      "day": 2,
      "round_trip": false,
      "description": "คำอธิบาย",
      "activities": []
    }}
  ],
  "days": [
    {{
      "day": 1,
      "activities": ["กิจกรรมรายวัน"],
      "accommodation_city": "เมืองที่พักคืนแรก"
    }},
    {{
      "day": 2,
      "activities": ["กิจกรรมรายวัน"],
      "accommodation_city": "เมืองที่พักคืนที่สอง"
    }}
  ]
}}

กฎ:
1. ถ้าผู้ใช้ระบุหลายเมือง ให้สร้างหลาย segments (A->B, B->C, etc.)
2. ถ้าเป็นทริปกลับ ให้สร้าง segment กลับด้วย (C->A)
3. แต่ละ segment ควรมี day number ที่ชัดเจน
4. activities ควรสอดคล้องกับ destination ของ segment นั้น
5. accommodation_city ควรเป็นเมืองที่พักในคืนนั้น

ตอบเฉพาะ JSON เท่านั้น ไม่ต้องมีคำอธิบายเพิ่มเติม"""

        try:
            response = await call_gemini(prompt)
            
            # Parse JSON from response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                route_data = json.loads(json_str)
                return route_data
            
            return None
        except Exception as e:
            import logging
            logging.error(f"Error analyzing route structure: {e}")
            return None
    
    @staticmethod
    async def _get_route_from_maps(segment_data: Dict[str, Any]) -> Optional[RouteSegment]:
        """Get actual route from Google Maps API"""
        origin = segment_data.get("origin", "")
        destination = segment_data.get("destination", "")
        day = segment_data.get("day", 1)
        mode = segment_data.get("mode", "driving")
        
        if not origin or not destination:
            return None
        
        # Get route from Google Maps
        route_result = await get_route(
            origin=origin,
            destination=destination,
            mode=mode,
            alternatives=False,
        )
        
        if not route_result.get("ok") or not route_result.get("routes"):
            # If Google Maps fails, create placeholder segment
            return RouteSegment(
                id=segment_data.get("id", f"segment_{day}"),
                origin=origin,
                destination=destination,
                day=day,
                mode=mode,
                distance_km=None,
                duration_hours=None,
                route_data=None,
            )
        
        selected_route = route_result["routes"][0]
        distance_km = selected_route.get("distance", 0) / 1000  # Convert to km
        duration_hours = selected_route.get("duration", 0) / 3600  # Convert to hours
        
        return RouteSegment(
            id=segment_data.get("id", f"segment_{day}"),
            origin=origin,
            destination=destination,
            day=day,
            mode=mode,
            distance_km=round(distance_km, 1),
            duration_hours=round(duration_hours, 1),
            route_data=selected_route,
        )
    
    @staticmethod
    def _calculate_date(start_date: str, days_offset: int) -> str:
        """Calculate date by adding days to start_date"""
        try:
            start = date.fromisoformat(start_date.split('T')[0])
            result = start + timedelta(days=days_offset)
            return result.isoformat()
        except:
            return start_date
    
    @staticmethod
    def _create_accommodation_slots(days: List[DayItinerary]) -> List[Dict[str, Any]]:
        """Create accommodation slots based on itinerary days"""
        slots = []
        seen_cities = set()
        
        for day in days:
            city = day.accommodation_city
            if city and city not in seen_cities:
                seen_cities.add(city)
                slots.append({
                    "city": city,
                    "check_in_date": day.date,
                    "day": day.day,
                    "nights": 1,  # Default 1 night, can be adjusted
                })
        
        return slots


async def plan_trip_itinerary(
    user_message: str,
    travel_slots: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> ItineraryPlan:
    """
    Convenience function to plan itinerary.
    """
    return await ItineraryPlanner.plan_itinerary(user_message, travel_slots, context)

