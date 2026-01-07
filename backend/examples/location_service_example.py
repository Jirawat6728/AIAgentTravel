"""
Example Usage of Location Service
Demonstrates geocoding, activities search, transfers, and IATA conversion
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.location_service import get_location_service


async def main():
    """Example usage of LocationService"""
    service = get_location_service()
    
    print("=" * 60)
    print("Location Service Examples")
    print("=" * 60)
    
    # Example 1: Geocoding
    print("\n1. Geocoding 'Eiffel Tower':")
    try:
        location = await service.geocode("Eiffel Tower")
        print(f"   Coordinates: {location.lat}, {location.lng}")
        print(f"   Address: {location.formatted_address}")
        print(f"   City: {location.city_name}")
        print(f"   Country: {location.country_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 2: Search Activities
    print("\n2. Searching activities near Eiffel Tower:")
    try:
        location = await service.geocode("Eiffel Tower")
        activities = await service.search_activities(location, radius=5000, max_results=5)
        print(f"   Found {len(activities)} activities:")
        for activity in activities:
            print(f"   - {activity.name} (Rating: {activity.rating})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 3: Search Transfers
    print("\n3. Searching transfers from Airport to Hotel:")
    try:
        start_loc, end_loc, transfers = await service.get_transfer_options(
            "Suvarnabhumi Airport",
            "Grand Palace Bangkok"
        )
        print(f"   From: {start_loc.formatted_address}")
        print(f"   To: {end_loc.formatted_address}")
        print(f"   Found {len(transfers)} transfer options:")
        for transfer in transfers:
            print(f"   - {transfer.name} ({transfer.vehicle_type})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 4: City to IATA Code
    print("\n4. Converting city names to IATA codes:")
    cities = ["Bangkok", "Paris", "Tokyo", "New York"]
    for city in cities:
        try:
            iata = await service.city_to_iata(city)
            print(f"   {city} -> {iata if iata else 'Not found'}")
        except Exception as e:
            print(f"   {city} -> Error: {e}")
    
    # Example 5: Convenience method (Geocode + Activities)
    print("\n5. One-call: Geocode + Activities for 'Grand Palace Bangkok':")
    try:
        location, activities = await service.get_location_with_activities(
            "Grand Palace Bangkok",
            radius=3000,
            max_activities=3
        )
        print(f"   Location: {location.formatted_address}")
        print(f"   Activities found: {len(activities)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

