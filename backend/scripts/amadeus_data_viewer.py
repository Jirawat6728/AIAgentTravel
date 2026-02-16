"""
Amadeus Data Viewer
Standalone script to fetch and display Amadeus data (Flights, Hotels, Transfers) in HTML
Uses production Amadeus API keys (AMADEUS_CLIENT_ID)

Usage:
    python -m scripts.amadeus_data_viewer
    Then open http://localhost:8080 in browser
"""

import asyncio
import httpx
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import uvicorn

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

# Import TravelOrchestrator for better integration
from app.services.travel_service import TravelOrchestrator
from app.core.config import settings

app = FastAPI(title="Amadeus Data Viewer")

# Use TravelOrchestrator (but override to use production)
orchestrator = TravelOrchestrator()
# Override to use production URL
orchestrator.amadeus_base_url = "https://api.amadeus.com"  # Production
orchestrator.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID") or settings.amadeus_api_key
orchestrator.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET") or settings.amadeus_api_secret

GOOGLE_MAPS_API_KEY = settings.google_maps_api_key or os.getenv("GOOGLE_MAPS_API_KEY", "")


async def search_flights(origin: str, destination: str, departure_date: str, adults: int = 1) -> List[Dict[str, Any]]:
    """Search flights from Amadeus using TravelOrchestrator"""
    try:
        # Use orchestrator's get_flights method
        flights = await orchestrator.get_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            adults=adults
        )
        return flights[:20]  # Limit to 20
    except Exception as e:
        print(f"Error fetching flights: {e}")
        return []


async def search_hotels(location_name: str, check_in: str, check_out: str, guests: int = 1) -> List[Dict[str, Any]]:
    """Search hotels from Amadeus using TravelOrchestrator"""
    try:
        # Use orchestrator's get_hotels method
        hotels = await orchestrator.get_hotels(
            location_name=location_name,
            check_in=check_in,
            check_out=check_out,
            guests=guests
        )
        return hotels[:20]  # Limit to 20
    except Exception as e:
        print(f"Error fetching hotels: {e}")
        return []


async def search_transfers(start_lat: float, start_lng: float, end_lat: float, end_lng: float, start_time: str) -> List[Dict[str, Any]]:
    """Search transfers from Amadeus using TravelOrchestrator"""
    try:
        # Use orchestrator's get_transfers_by_geo method
        transfers = await orchestrator.get_transfers_by_geo(
            start_lat=start_lat,
            start_lng=start_lng,
            end_lat=end_lat,
            end_lng=end_lng,
            start_time=start_time,
            passengers=1
        )
        return transfers[:20]  # Limit to 20
    except Exception as e:
        print(f"Error fetching transfers: {e}")
        return []


async def geocode_location(location: str) -> Optional[Dict[str, float]]:
    """Geocode location using TravelOrchestrator"""
    try:
        # Use orchestrator's get_coordinates method
        coords = await orchestrator.get_coordinates(location)
        return {"lat": coords["lat"], "lng": coords["lng"]}
    except Exception as e:
        print(f"Error geocoding: {e}")
    return None


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page with form"""
    html = """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amadeus Data Viewer</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { opacity: 0.9; }
            .form-section {
                padding: 40px;
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
            .form-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .form-group {
                display: flex;
                flex-direction: column;
            }
            .form-group label {
                font-weight: 600;
                margin-bottom: 8px;
                color: #495057;
            }
            .form-group input, .form-group select {
                padding: 12px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .btn:active { transform: translateY(0); }
            .results-section {
                padding: 40px;
            }
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
                border-bottom: 2px solid #dee2e6;
            }
            .tab {
                padding: 15px 30px;
                background: none;
                border: none;
                font-size: 16px;
                font-weight: 600;
                color: #6c757d;
                cursor: pointer;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }
            .tab.active {
                color: #667eea;
                border-bottom-color: #667eea;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .data-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .data-card {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 20px;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .data-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }
            .data-card h3 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.3em;
            }
            .data-card .price {
                font-size: 1.8em;
                font-weight: bold;
                color: #28a745;
                margin: 10px 0;
            }
            .data-card .detail {
                margin: 8px 0;
                color: #6c757d;
            }
            .map-container {
                width: 100%;
                height: 500px;
                border-radius: 12px;
                margin-top: 30px;
                border: 2px solid #dee2e6;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #6c757d;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✈️ Amadeus Data Viewer</h1>
                <p>ดึงข้อมูล Flights, Hotels, และ Transfers จาก Amadeus Production API</p>
            </div>
            
            <div class="form-section">
                <form id="searchForm" method="POST" action="/search">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>ต้นทาง (Origin)</label>
                            <input type="text" name="origin" placeholder="BKK, DMK, หรือชื่อเมือง" required>
                        </div>
                        <div class="form-group">
                            <label>ปลายทาง (Destination)</label>
                            <input type="text" name="destination" placeholder="ICN, NRT, หรือชื่อเมือง" required>
                        </div>
                        <div class="form-group">
                            <label>วันที่เดินทาง</label>
                            <input type="date" name="departure_date" required>
                        </div>
                        <div class="form-group">
                            <label>จำนวนผู้โดยสาร</label>
                            <input type="number" name="adults" value="1" min="1" max="9" required>
                        </div>
                    </div>
                    <button type="submit" class="btn">🔍 ค้นหาข้อมูล</button>
                </form>
            </div>
            
            <div class="results-section" id="results" style="display: none;">
                <div class="tabs">
                    <button class="tab active" onclick="showTab('flights')">✈️ เที่ยวบิน</button>
                    <button class="tab" onclick="showTab('hotels')">🏨 โรงแรม</button>
                    <button class="tab" onclick="showTab('transfers')">🚗 รถรับส่ง</button>
                    <button class="tab" onclick="showTab('map')">🗺️ แผนที่</button>
                </div>
                
                <div id="flights" class="tab-content active">
                    <div class="data-grid" id="flightsGrid"></div>
                </div>
                
                <div id="hotels" class="tab-content">
                    <div class="data-grid" id="hotelsGrid"></div>
                </div>
                
                <div id="transfers" class="tab-content">
                    <div class="data-grid" id="transfersGrid"></div>
                </div>
                
                <div id="map" class="tab-content">
                    <div class="map-container" id="mapContainer"></div>
                </div>
            </div>
        </div>
        
        <script>
            function showTab(tabName) {
                // Hide all tabs
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                
                // Show selected tab
                document.getElementById(tabName).classList.add('active');
                event.target.classList.add('active');
                
                // Initialize map if map tab
                if (tabName === 'map' && typeof initMap === 'function') {
                    initMap();
                }
            }
        </script>
        <script src="https://maps.googleapis.com/maps/api/js?key=""" + GOOGLE_MAPS_API_KEY + """&libraries=places,geometry"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/search", response_class=HTMLResponse)
async def search(
    origin: str = Form(...),
    destination: str = Form(...),
    departure_date: str = Form(...),
    adults: int = Form(1)
):
    """Search and return results"""
    
    # Calculate check-out date (4 days from departure)
    dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
    check_in = departure_date
    check_out = (dep_date + timedelta(days=4)).strftime("%Y-%m-%d")
    
    # Convert location names to IATA codes if needed
    origin_code = origin.upper()[:3] if len(origin) == 3 and origin.isupper() else await orchestrator.find_city_iata(origin) or origin
    dest_code = destination.upper()[:3] if len(destination) == 3 and destination.isupper() else await orchestrator.find_city_iata(destination) or destination
    
    # Fetch data concurrently
    flights_task = search_flights(origin_code, dest_code, departure_date, adults)
    hotels_task = search_hotels(destination, check_in, check_out, adults)  # Use location_name for hotels
    
    # Geocode for transfers and map
    origin_geo = await geocode_location(origin)
    dest_geo = await geocode_location(destination)
    
    transfers_task = None
    if origin_geo and dest_geo:
        start_time = f"{departure_date}T10:00:00"
        transfers_task = search_transfers(
            origin_geo["lat"], origin_geo["lng"],
            dest_geo["lat"], dest_geo["lng"],
            start_time
        )
    
    # Wait for all tasks
    results = await asyncio.gather(
        flights_task,
        hotels_task,
        transfers_task if transfers_task else asyncio.sleep(0)
    )
    
    flights = results[0]
    hotels = results[1]
    transfers = results[2] if transfers_task else []
    
    # Generate HTML
    html = generate_results_html(flights, hotels, transfers, origin, destination, origin_geo, dest_geo)
    return HTMLResponse(content=html)


def generate_results_html(
    flights: List[Dict],
    hotels: List[Dict],
    transfers: List[Dict],
    origin: str,
    destination: str,
    origin_geo: Optional[Dict],
    dest_geo: Optional[Dict]
) -> str:
    """Generate HTML with results"""
    
    # Flights HTML
    flights_html = ""
    for flight in flights[:20]:  # Limit to 20
        price = flight.get("price", {}).get("total", "N/A")
        currency = flight.get("price", {}).get("currency", "THB")
        itineraries = flight.get("itineraries", [])
        segments = itineraries[0].get("segments", []) if itineraries else []
        
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}
        
        flights_html += f"""
        <div class="data-card">
            <h3>{first_seg.get('carrierCode', 'N/A')} {first_seg.get('number', 'N/A')}</h3>
            <div class="price">{currency} {price}</div>
            <div class="detail">🛫 {first_seg.get('departure', {}).get('iataCode', 'N/A')} → {last_seg.get('arrival', {}).get('iataCode', 'N/A')}</div>
            <div class="detail">⏰ {itineraries[0].get('duration', 'N/A') if itineraries else 'N/A'}</div>
            <div class="detail">🔄 {len(segments) - 1} ต่อเครื่อง</div>
        </div>
        """
    
    # Hotels HTML
    hotels_html = ""
    for hotel in hotels[:20]:  # Limit to 20
        hotel_info = hotel.get("hotel", {})
        offers = hotel.get("offers", [])
        offer = offers[0] if offers else {}
        price = offer.get("price", {}).get("total", "N/A")
        currency = offer.get("price", {}).get("currency", "THB")
        
        hotels_html += f"""
        <div class="data-card">
            <h3>{hotel_info.get('name', 'N/A')}</h3>
            <div class="price">{currency} {price}</div>
            <div class="detail">⭐ {hotel_info.get('rating', 'N/A')}</div>
            <div class="detail">📍 {hotel_info.get('address', {}).get('lines', ['N/A'])[0]}</div>
        </div>
        """
    
    # Transfers HTML
    transfers_html = ""
    for transfer in transfers[:20]:  # Limit to 20
        price = transfer.get("price", {}).get("total", "N/A")
        currency = transfer.get("price", {}).get("currency", "THB")
        vehicle = transfer.get("vehicle", {})
        
        transfers_html += f"""
        <div class="data-card">
            <h3>{vehicle.get('name', 'Transfer')}</h3>
            <div class="price">{currency} {price}</div>
            <div class="detail">🚗 {vehicle.get('type', 'N/A')}</div>
            <div class="detail">👥 {transfer.get('passengers', 1)} ที่นั่ง</div>
        </div>
        """
    
    # Map script
    map_script = ""
    if origin_geo and dest_geo:
        map_script = f"""
        <script>
            function initMap() {{
                const map = new google.maps.Map(document.getElementById('mapContainer'), {{
                    zoom: 6,
                    center: {{ lat: {(origin_geo['lat'] + dest_geo['lat']) / 2}, lng: {(origin_geo['lng'] + dest_geo['lng']) / 2} }}
                }});
                
                const originMarker = new google.maps.Marker({{
                    position: {{ lat: {origin_geo['lat']}, lng: {origin_geo['lng']} }},
                    map: map,
                    title: '{origin}',
                    icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
                }});
                
                const destMarker = new google.maps.Marker({{
                    position: {{ lat: {dest_geo['lat']}, lng: {dest_geo['lng']} }},
                    map: map,
                    title: '{destination}',
                    icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
                }});
                
                const directionsService = new google.maps.DirectionsService();
                const directionsRenderer = new google.maps.DirectionsRenderer({{
                    map: map,
                    suppressMarkers: false
                }});
                
                directionsService.route({{
                    origin: {{ lat: {origin_geo['lat']}, lng: {origin_geo['lng']} }},
                    destination: {{ lat: {dest_geo['lat']}, lng: {dest_geo['lng']} }},
                    travelMode: google.maps.TravelMode.DRIVING
                }}, (result, status) => {{
                    if (status === 'OK') {{
                        directionsRenderer.setDirections(result);
                    }}
                }});
            }}
            // Auto-init map on load
            window.onload = function() {{
                if (document.getElementById('map').classList.contains('active')) {{
                    initMap();
                }}
            }};
        </script>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amadeus Data Viewer - Results</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
            .header p {{ opacity: 0.9; }}
            .form-section {{
                padding: 40px;
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }}
            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .form-group {{
                display: flex;
                flex-direction: column;
            }}
            .form-group label {{
                font-weight: 600;
                margin-bottom: 8px;
                color: #495057;
            }}
            .form-group input, .form-group select {{
                padding: 12px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }}
            .form-group input:focus, .form-group select:focus {{
                outline: none;
                border-color: #667eea;
            }}
            .btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }}
            .results-section {{
                padding: 40px;
            }}
            .tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
                border-bottom: 2px solid #dee2e6;
            }}
            .tab {{
                padding: 15px 30px;
                background: none;
                border: none;
                font-size: 16px;
                font-weight: 600;
                color: #6c757d;
                cursor: pointer;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }}
            .tab.active {{
                color: #667eea;
                border-bottom-color: #667eea;
            }}
            .tab-content {{
                display: none;
            }}
            .tab-content.active {{
                display: block;
            }}
            .data-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .data-card {{
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 20px;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .data-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }}
            .data-card h3 {{
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.3em;
            }}
            .data-card .price {{
                font-size: 1.8em;
                font-weight: bold;
                color: #28a745;
                margin: 10px 0;
            }}
            .data-card .detail {{
                margin: 8px 0;
                color: #6c757d;
            }}
            .map-container {{
                width: 100%;
                height: 500px;
                border-radius: 12px;
                margin-top: 30px;
                border: 2px solid #dee2e6;
            }}
            .summary {{
                background: #e7f3ff;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 30px;
            }}
            .summary h2 {{
                color: #667eea;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✈️ Amadeus Data Viewer</h1>
                <p>ผลการค้นหา: {origin} → {destination}</p>
            </div>
            
            <div class="form-section">
                <form method="POST" action="/search">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>ต้นทาง (Origin)</label>
                            <input type="text" name="origin" value="{origin}" required>
                        </div>
                        <div class="form-group">
                            <label>ปลายทาง (Destination)</label>
                            <input type="text" name="destination" value="{destination}" required>
                        </div>
                        <div class="form-group">
                            <label>วันที่เดินทาง</label>
                            <input type="date" name="departure_date" value="{departure_date}" required>
                        </div>
                        <div class="form-group">
                            <label>จำนวนผู้โดยสาร</label>
                            <input type="number" name="adults" value="1" min="1" max="9" required>
                        </div>
                    </div>
                    <button type="submit" class="btn">🔍 ค้นหาใหม่</button>
                </form>
            </div>
            
            <div class="results-section">
                <div class="summary">
                    <h2>📊 สรุปผลการค้นหา</h2>
                    <p>✈️ เที่ยวบิน: {len(flights)} รายการ</p>
                    <p>🏨 โรงแรม: {len(hotels)} รายการ</p>
                    <p>🚗 รถรับส่ง: {len(transfers)} รายการ</p>
                </div>
                
                <div class="tabs">
                    <button class="tab active" onclick="showTab('flights')">✈️ เที่ยวบิน ({len(flights)})</button>
                    <button class="tab" onclick="showTab('hotels')">🏨 โรงแรม ({len(hotels)})</button>
                    <button class="tab" onclick="showTab('transfers')">🚗 รถรับส่ง ({len(transfers)})</button>
                    <button class="tab" onclick="showTab('map')">🗺️ แผนที่</button>
                </div>
                
                <div id="flights" class="tab-content active">
                    <div class="data-grid">
                        {flights_html if flights_html else '<div class="loading">ไม่พบข้อมูลเที่ยวบิน</div>'}
                    </div>
                </div>
                
                <div id="hotels" class="tab-content">
                    <div class="data-grid">
                        {hotels_html if hotels_html else '<div class="loading">ไม่พบข้อมูลโรงแรม</div>'}
                    </div>
                </div>
                
                <div id="transfers" class="tab-content">
                    <div class="data-grid">
                        {transfers_html if transfers_html else '<div class="loading">ไม่พบข้อมูลรถรับส่ง</div>'}
                    </div>
                </div>
                
                <div id="map" class="tab-content">
                    <div class="map-container" id="mapContainer"></div>
                </div>
            </div>
        </div>
        
        <script>
            function showTab(tabName) {{
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.getElementById(tabName).classList.add('active');
                event.target.classList.add('active');
                if (tabName === 'map' && typeof initMap === 'function') {{
                    initMap();
                }}
            }}
        </script>
        <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=places,geometry"></script>
        {map_script}
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    import time
    print("Starting Amadeus Data Viewer on http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
