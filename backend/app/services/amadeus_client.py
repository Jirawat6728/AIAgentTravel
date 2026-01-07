"""
Amadeus Transfer Service
Production-grade service for handling Transfer and Water Activities via Amadeus API
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import logging

from pydantic import BaseModel, Field, field_validator
from amadeus import Client, ResponseError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AmadeusException

logger = get_logger(__name__)


# =============================================================================
# Pydantic Models for Input/Output
# =============================================================================

class GroundTransferRequest(BaseModel):
    """Request model for ground transfer search"""
    start_location_code: str = Field(..., description="IATA airport code (e.g., 'BKK')")
    end_address_line: str = Field(..., description="Destination address")
    start_date_time: str = Field(..., description="Transfer date/time in ISO 8601 format")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    
    @field_validator('start_location_code')
    @classmethod
    def validate_iata_code(cls, v: str) -> str:
        """Validate IATA code format"""
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"Invalid IATA code format: {v}")
        return v


class WaterActivityRequest(BaseModel):
    """Request model for water activity search"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    radius: int = Field(default=5000, ge=100, le=50000, description="Search radius in meters")


class TransferOption(BaseModel):
    """Standardized transfer option model"""
    id: str = Field(..., description="Transfer option ID")
    type: str = Field(..., description="Transfer type: 'PRIVATE', 'TAXI', 'RAIL', or 'SHARED'")
    name: str = Field(..., description="Transfer name/description")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type (e.g., 'SEDAN', 'SUV')")
    price: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    currency: Optional[str] = Field(None, description="Currency code")
    duration: Optional[str] = Field(None, description="Estimated duration")
    distance: Optional[float] = Field(None, description="Distance in kilometers")
    provider: Optional[str] = Field(None, description="Service provider name")


class WaterActivity(BaseModel):
    """Standardized water activity model"""
    id: str = Field(..., description="Activity ID")
    name: str = Field(..., description="Activity name")
    description: Optional[str] = Field(None, description="Activity description")
    category: str = Field(default="WATER", description="Activity category")
    price: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Activity rating")
    location: Optional[Dict[str, float]] = Field(None, description="Location coordinates")


class TransferSearchResponse(BaseModel):
    """Standardized response for transfer search"""
    options: List[TransferOption] = Field(default_factory=list, description="List of transfer options")
    private_transfers: List[TransferOption] = Field(default_factory=list, description="Private transfer options")
    taxi_transfers: List[TransferOption] = Field(default_factory=list, description="Taxi transfer options")
    rail_transfers: List[TransferOption] = Field(default_factory=list, description="Airport rail options")
    total_count: int = Field(default=0, description="Total number of options found")


class WaterActivityResponse(BaseModel):
    """Standardized response for water activity search"""
    activities: List[WaterActivity] = Field(default_factory=list, description="List of water activities")
    total_count: int = Field(default=0, description="Total number of activities found")


# =============================================================================
# Amadeus Transfer Service
# =============================================================================

class AmadeusTransferService:
    """
    Production-Grade Amadeus Transfer Service
    Handles ground transfers (Private, Taxi, Rail) and water activities (Boat Tours/Cruises)
    """
    
    def __init__(self):
        """Initialize Amadeus client"""
        if not settings.amadeus_api_key or not settings.amadeus_api_secret:
            logger.warning("Amadeus API credentials not configured")
            self.amadeus = None
        else:
            try:
                self.amadeus = Client(
                    client_id=settings.amadeus_api_key,
                    client_secret=settings.amadeus_api_secret,
                    hostname=settings.amadeus_env
                )
                logger.info("AmadeusTransferService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Amadeus client: {e}")
                self.amadeus = None
    
    async def search_ground_transfers(
        self,
        request: GroundTransferRequest
    ) -> TransferSearchResponse:
        """
        Search for ground transfer options (Private, Taxi, Rail)
        
        Args:
            request: GroundTransferRequest with IATA code, address, datetime, passengers
            
        Returns:
            TransferSearchResponse with categorized transfer options
            
        Raises:
            AmadeusException: If API call fails
        """
        if not self.amadeus:
            raise AmadeusException("Amadeus API not configured")
        
        try:
            # Run Amadeus API call in thread pool
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    # Call /v1/shopping/transfer-offers endpoint
                    response = self.amadeus.shopping.transfer_offers.get(
                        startLocationCode=request.start_location_code,
                        endAddressLine=request.end_address_line,
                        startDateTime=request.start_date_time,
                        passengers=request.passengers
                    )
                    return response.data if hasattr(response, 'data') else []
                except ResponseError as e:
                    logger.error(f"Amadeus Transfer API error: {e}")
                    # Check error type
                    if e.response and hasattr(e.response, 'status_code'):
                        if e.response.status_code == 400:
                            raise AmadeusException(f"Bad Request: {e.description}")
                        elif e.response.status_code == 401:
                            raise AmadeusException("Unauthorized: Invalid API credentials")
                        elif e.response.status_code == 404:
                            raise AmadeusException("Transfer options not found")
                    raise AmadeusException(f"Amadeus API error: {e.description}")
            
            transfer_data = await loop.run_in_executor(None, _search)
            
            if not transfer_data:
                logger.warning(f"No transfers found from {request.start_location_code} to {request.end_address_line}")
                return TransferSearchResponse()
            
            # Format and categorize transfers
            return self._format_transfer_response(transfer_data)
        
        except AmadeusException:
            raise
        except Exception as e:
            logger.error(f"Ground transfer search error: {e}", exc_info=True)
            raise AmadeusException(f"Failed to search ground transfers: {str(e)}") from e
    
    async def search_water_activities(
        self,
        request: WaterActivityRequest
    ) -> WaterActivityResponse:
        """
        Search for water activities (Boat Tours, Cruises, Ferries)
        
        Args:
            request: WaterActivityRequest with latitude, longitude, radius
            
        Returns:
            WaterActivityResponse with filtered water activities
            
        Raises:
            AmadeusException: If API call fails
        """
        if not self.amadeus:
            raise AmadeusException("Amadeus API not configured")
        
        try:
            # Run Amadeus API call in thread pool
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    # Call /v1/shopping/activities endpoint
                    response = self.amadeus.shopping.activities.get(
                        latitude=request.latitude,
                        longitude=request.longitude,
                        radius=request.radius
                    )
                    return response.data if hasattr(response, 'data') else []
                except ResponseError as e:
                    logger.error(f"Amadeus Activities API error: {e}")
                    if e.response and hasattr(e.response, 'status_code'):
                        if e.response.status_code == 400:
                            raise AmadeusException(f"Bad Request: {e.description}")
                        elif e.response.status_code == 401:
                            raise AmadeusException("Unauthorized: Invalid API credentials")
                    raise AmadeusException(f"Amadeus API error: {e.description}")
            
            activities_data = await loop.run_in_executor(None, _search)
            
            if not activities_data:
                logger.warning(f"No activities found at {request.latitude},{request.longitude}")
                return WaterActivityResponse()
            
            # Filter water-related activities
            water_activities = self._filter_water_activities(activities_data)
            
            # Convert to WaterActivity objects
            results = []
            for activity in water_activities:
                try:
                    # Handle both dict and object responses
                    if isinstance(activity, dict):
                        activity_dict = activity
                    else:
                        activity_dict = activity.__dict__ if hasattr(activity, '__dict__') else {}
                    
                    result = WaterActivity(
                        id=activity_dict.get("id", ""),
                        name=activity_dict.get("name", "Unknown Activity"),
                        description=activity_dict.get("description", {}).get("short", "") if isinstance(activity_dict.get("description"), dict) else "",
                        price=activity_dict.get("price"),
                        rating=activity_dict.get("rating"),
                        location=activity_dict.get("geoCode")
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse activity: {e}")
                    continue
            
            logger.info(f"Found {len(results)} water activities")
            return WaterActivityResponse(activities=results, total_count=len(results))
        
        except AmadeusException:
            raise
        except Exception as e:
            logger.error(f"Water activity search error: {e}", exc_info=True)
            raise AmadeusException(f"Failed to search water activities: {str(e)}") from e
    
    def _filter_water_activities(self, activities: List[Any]) -> List[Any]:
        """
        Filter activities to only include water-related ones
        
        Args:
            activities: List of activity objects/dicts
            
        Returns:
            Filtered list of water activities
        """
        water_keywords = ['boat', 'cruise', 'ferry', 'yacht', 'sailing', 'kayak', 'canoe', 'water', 'marine', 'nautical']
        filtered = []
        
        for activity in activities:
            # Handle both dict and object
            if isinstance(activity, dict):
                activity_dict = activity
            else:
                activity_dict = activity.__dict__ if hasattr(activity, '__dict__') else {}
            
            # Check name and description
            name = str(activity_dict.get("name", "")).lower()
            description = ""
            desc_obj = activity_dict.get("description", {})
            if isinstance(desc_obj, dict):
                description = str(desc_obj.get("short", "") + " " + desc_obj.get("long", "")).lower()
            else:
                description = str(desc_obj).lower()
            
            # Check if any keyword matches
            text_to_check = f"{name} {description}"
            if any(keyword in text_to_check for keyword in water_keywords):
                filtered.append(activity)
        
        logger.info(f"Filtered {len(filtered)} water activities from {len(activities)} total activities")
        return filtered
    
    def _format_transfer_response(self, transfer_data: List[Any]) -> TransferSearchResponse:
        """
        Format and categorize transfer options into standardized response
        
        Args:
            transfer_data: Raw transfer data from Amadeus API
            
        Returns:
            TransferSearchResponse with categorized options
        """
        private_transfers = []
        taxi_transfers = []
        rail_transfers = []
        all_options = []
        
        for transfer in transfer_data:
            try:
                # Handle both dict and object responses
                if isinstance(transfer, dict):
                    transfer_dict = transfer
                else:
                    transfer_dict = transfer.__dict__ if hasattr(transfer, '__dict__') else {}
                
                # Extract vehicle type
                vehicle_type_raw = transfer_dict.get("vehicleType", "")
                vehicle_type = str(vehicle_type_raw).upper() if vehicle_type_raw else ""
                
                # Determine transfer type
                transfer_type = "SHARED"
                if "PRIVATE" in vehicle_type or "SEDAN" in vehicle_type or "SUV" in vehicle_type or "VAN" in vehicle_type:
                    transfer_type = "PRIVATE"
                elif "TAXI" in vehicle_type:
                    transfer_type = "TAXI"
                elif "RAIL" in vehicle_type or "TRAIN" in vehicle_type or "METRO" in vehicle_type:
                    transfer_type = "RAIL"
                
                # Extract price information
                price_info = transfer_dict.get("price", {})
                if isinstance(price_info, dict):
                    price = price_info
                else:
                    price = {"total": str(price_info)} if price_info else None
                
                # Create TransferOption
                option = TransferOption(
                    id=transfer_dict.get("id", ""),
                    type=transfer_type,
                    name=transfer_dict.get("name", "Unknown Transfer"),
                    vehicle_type=vehicle_type if vehicle_type else None,
                    price=price,
                    currency=price.get("currency") if price else None,
                    duration=transfer_dict.get("duration"),
                    distance=transfer_dict.get("distance"),
                    provider=transfer_dict.get("provider", {}).get("name") if isinstance(transfer_dict.get("provider"), dict) else None
                )
                
                all_options.append(option)
                
                # Categorize
                if transfer_type == "PRIVATE":
                    private_transfers.append(option)
                elif transfer_type == "TAXI":
                    taxi_transfers.append(option)
                elif transfer_type == "RAIL":
                    rail_transfers.append(option)
                
            except Exception as e:
                logger.warning(f"Failed to parse transfer option: {e}")
                continue
        
        logger.info(f"Formatted {len(all_options)} transfer options: {len(private_transfers)} private, {len(taxi_transfers)} taxi, {len(rail_transfers)} rail")
        
        return TransferSearchResponse(
            options=all_options,
            private_transfers=private_transfers,
            taxi_transfers=taxi_transfers,
            rail_transfers=rail_transfers,
            total_count=len(all_options)
        )


# Global instance
_amadeus_transfer_service: Optional[AmadeusTransferService] = None


def get_amadeus_transfer_service() -> AmadeusTransferService:
    """Get or create global AmadeusTransferService instance"""
    global _amadeus_transfer_service
    if _amadeus_transfer_service is None:
        _amadeus_transfer_service = AmadeusTransferService()
    return _amadeus_transfer_service

