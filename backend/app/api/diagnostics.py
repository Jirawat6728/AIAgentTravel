"""
Diagnostic API endpoints for troubleshooting search issues
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio

from app.core.logging import get_logger
from app.core.config import settings
from app.services.travel_service import TravelOrchestrator
from app.services.mcp_server import MCPToolExecutor

logger = get_logger(__name__)
router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("/search-status")
async def get_search_status() -> Dict[str, Any]:
    """
    Diagnostic endpoint to check search service status
    Returns API key status, connectivity, and test results
    """
    amadeus_key = settings.amadeus_search_api_key or settings.amadeus_api_key
    amadeus_secret = settings.amadeus_search_api_secret or settings.amadeus_api_secret
    
    status = {
        "amadeus": {
            "api_key_configured": bool(amadeus_key),
            "api_secret_configured": bool(amadeus_secret),
            "token_available": False,
            "connection_test": "not_tested"
        },
        "google_maps": {
            "api_key_configured": bool(settings.google_maps_api_key),
            "connection_test": "not_tested"
        },
        "overall": {
            "status": "unknown",
            "issues": []
        }
    }
    
    issues = []
    
    # Test Amadeus API
    if not amadeus_key or not amadeus_secret:
        issues.append("Amadeus API keys not configured")
        status["amadeus"]["connection_test"] = "failed"
    else:
        try:
            travel_service = TravelOrchestrator()
            token = await travel_service._get_amadeus_token()
            if token:
                status["amadeus"]["token_available"] = True
                status["amadeus"]["connection_test"] = "success"
            else:
                issues.append("Amadeus token generation failed")
                status["amadeus"]["connection_test"] = "failed"
        except Exception as e:
            issues.append(f"Amadeus connection error: {str(e)}")
            status["amadeus"]["connection_test"] = "failed"
            logger.error(f"Amadeus diagnostic error: {e}", exc_info=True)
    
    # Test Google Maps API
    if not settings.google_maps_api_key:
        issues.append("Google Maps API key not configured")
        status["google_maps"]["connection_test"] = "failed"
    else:
        try:
            travel_service = TravelOrchestrator()
            # Test geocoding with a simple query
            test_result = await travel_service.get_coordinates("Bangkok")
            if test_result and "lat" in test_result:
                status["google_maps"]["connection_test"] = "success"
            else:
                issues.append("Google Maps geocoding test failed")
                status["google_maps"]["connection_test"] = "failed"
        except Exception as e:
            issues.append(f"Google Maps connection error: {str(e)}")
            status["google_maps"]["connection_test"] = "failed"
            logger.error(f"Google Maps diagnostic error: {e}", exc_info=True)
    
    # Overall status
    if not issues:
        status["overall"]["status"] = "healthy"
    elif len(issues) == 1 and "not configured" in issues[0]:
        status["overall"]["status"] = "partially_configured"
    else:
        status["overall"]["status"] = "unhealthy"
    
    status["overall"]["issues"] = issues
    
    return status


@router.get("/test-search")
async def test_search(
    origin: str = "Bangkok",
    destination: str = "Phuket",
    date: str = None
) -> Dict[str, Any]:
    """
    Test search functionality with sample query
    """
    from datetime import datetime, timedelta
    
    if not date:
        date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    result = {
        "test_params": {
            "origin": origin,
            "destination": destination,
            "date": date
        },
        "iata_resolution": {
            "origin_code": None,
            "destination_code": None,
            "status": "not_tested"
        },
        "flight_search": {
            "status": "not_tested",
            "results_count": 0,
            "error": None
        },
        "hotel_search": {
            "status": "not_tested",
            "results_count": 0,
            "error": None
        }
    }
    
    try:
        travel_service = TravelOrchestrator()
        
        # Test IATA resolution
        try:
            origin_code = await travel_service._city_to_iata_sync(origin)
            dest_code = await travel_service._city_to_iata_sync(destination)
            result["iata_resolution"]["origin_code"] = origin_code
            result["iata_resolution"]["destination_code"] = dest_code
            
            if origin_code and dest_code:
                result["iata_resolution"]["status"] = "success"
            else:
                result["iata_resolution"]["status"] = "partial_failure"
                if not origin_code:
                    result["iata_resolution"]["origin_error"] = f"Could not resolve IATA for '{origin}'"
                if not dest_code:
                    result["iata_resolution"]["destination_error"] = f"Could not resolve IATA for '{destination}'"
        except Exception as e:
            result["iata_resolution"]["status"] = "failed"
            result["iata_resolution"]["error"] = str(e)
            logger.error(f"IATA resolution test failed: {e}", exc_info=True)
        
        # Test flight search (if IATA codes resolved)
        if result["iata_resolution"]["status"] == "success":
            try:
                flights = await travel_service.get_flights(
                    origin=origin_code,
                    destination=dest_code,
                    departure_date=date,
                    adults=1
                )
                result["flight_search"]["results_count"] = len(flights) if flights else 0
                result["flight_search"]["status"] = "success" if flights else "no_results"
            except Exception as e:
                result["flight_search"]["status"] = "failed"
                result["flight_search"]["error"] = str(e)
                logger.error(f"Flight search test failed: {e}", exc_info=True)
        else:
            result["flight_search"]["status"] = "skipped"
            result["flight_search"]["error"] = "IATA resolution failed"
        
        # Test hotel search
        try:
            check_in = date
            check_out = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
            hotels = await travel_service.get_hotels(
                location_name=destination,
                check_in=check_in,
                check_out=check_out,
                guests=1
            )
            result["hotel_search"]["results_count"] = len(hotels) if hotels else 0
            result["hotel_search"]["status"] = "success" if hotels else "no_results"
        except Exception as e:
            result["hotel_search"]["status"] = "failed"
            result["hotel_search"]["error"] = str(e)
            logger.error(f"Hotel search test failed: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Test search failed: {e}", exc_info=True)
        result["error"] = str(e)
    
    return result
