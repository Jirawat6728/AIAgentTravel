"""
Example Usage of Amadeus Transfer Service
Demonstrates ground transfers and water activities integration
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.amadeus_client import (
    get_amadeus_transfer_service,
    GroundTransferRequest,
    WaterActivityRequest
)
from app.services.google_maps_client import get_location_for_transfer


async def main():
    """Example usage of Amadeus Transfer Service"""
    print("=" * 60)
    print("Amadeus Transfer Service Examples")
    print("=" * 60)
    
    # Example 1: Get location information for transfer
    print("\n1. Getting location information for transfer:")
    try:
        location_info = await get_location_for_transfer("Grand Palace Bangkok")
        print(f"   Address: {location_info['formatted_address']}")
        print(f"   Coordinates: {location_info['latitude']}, {location_info['longitude']}")
        print(f"   Nearest Airport: {location_info['airport_name']} ({location_info['iata_code']})")
        print(f"   Distance to Airport: {location_info['airport_distance']:.0f}m" if location_info['airport_distance'] else "   Distance: N/A")
    except Exception as e:
        print(f"   Error: {e}")
        location_info = None
    
    # Example 2: Search ground transfers
    if location_info and location_info.get('iata_code'):
        print(f"\n2. Searching ground transfers from {location_info['iata_code']} to Grand Palace:")
        try:
            service = get_amadeus_transfer_service()
            
            # Create transfer request
            start_datetime = (datetime.now() + timedelta(days=1)).isoformat()
            request = GroundTransferRequest(
                start_location_code=location_info['iata_code'],
                end_address_line=location_info['formatted_address'],
                start_date_time=start_datetime,
                passengers=2
            )
            
            # Search transfers
            response = await service.search_ground_transfers(request)
            
            print(f"   Total options: {response.total_count}")
            print(f"   Private transfers: {len(response.private_transfers)}")
            print(f"   Taxi transfers: {len(response.taxi_transfers)}")
            print(f"   Rail transfers: {len(response.rail_transfers)}")
            
            # Show sample options
            if response.private_transfers:
                print("\n   Sample Private Transfer:")
                sample = response.private_transfers[0]
                print(f"   - {sample.name} ({sample.vehicle_type})")
                if sample.price:
                    print(f"     Price: {sample.price}")
            
            if response.rail_transfers:
                print("\n   Sample Rail Transfer:")
                sample = response.rail_transfers[0]
                print(f"   - {sample.name}")
                if sample.duration:
                    print(f"     Duration: {sample.duration}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Example 3: Search water activities
    print("\n3. Searching water activities near a location:")
    try:
        service = get_amadeus_transfer_service()
        
        # Use coordinates from location info or default to a known location
        if location_info:
            lat = location_info['latitude']
            lng = location_info['longitude']
        else:
            # Default: Phuket (for boat tours example)
            lat = 7.8804
            lng = 98.3923
        
        request = WaterActivityRequest(
            latitude=lat,
            longitude=lng,
            radius=10000  # 10km
        )
        
        response = await service.search_water_activities(request)
        
        print(f"   Found {response.total_count} water activities")
        for activity in response.activities[:5]:  # Show first 5
            print(f"   - {activity.name}")
            if activity.rating:
                print(f"     Rating: {activity.rating}/5")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 4: Complete workflow
    print("\n4. Complete workflow: Location -> Transfers + Activities:")
    try:
        # Get location
        location = await get_location_for_transfer("Eiffel Tower")
        print(f"   Location: {location['formatted_address']}")
        
        # Search transfers (if airport code available)
        if location.get('iata_code'):
            service = get_amadeus_transfer_service()
            transfer_request = GroundTransferRequest(
                start_location_code=location['iata_code'],
                end_address_line=location['formatted_address'],
                start_date_time=(datetime.now() + timedelta(days=1)).isoformat(),
                passengers=2
            )
            transfer_response = await service.search_ground_transfers(transfer_request)
            print(f"   Transfer options: {transfer_response.total_count}")
        
        # Search water activities
        service = get_amadeus_transfer_service()
        activity_request = WaterActivityRequest(
            latitude=location['latitude'],
            longitude=location['longitude'],
            radius=5000
        )
        activity_response = await service.search_water_activities(activity_request)
        print(f"   Water activities: {activity_response.total_count}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

