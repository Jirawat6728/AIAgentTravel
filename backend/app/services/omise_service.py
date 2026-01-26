"""
Omise Payment Service
Handles integration with Omise Payment Gateway
"""

import httpx
import os
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import get_logger
from app.core.resilience import omise_circuit_breaker

logger = get_logger(__name__)

class OmiseService:
    @staticmethod
    async def _create_checkout_internal(booking_id: str, amount: float, currency: str = "THB", request_base_url: str = None) -> str:
        """
        Internal method to create Omise checkout (wrapped by circuit breaker)
        """
        """
        Create Omise Checkout Session and return payment URL
        
        Args:
            booking_id: Booking ID
            amount: Payment amount
            currency: Currency code (default: THB)
            
        Returns:
            Omise checkout URL
        """
        try:
            # Check if Omise keys are configured
            if not settings.omise_secret_key:
                # Try reloading .env explicitly if keys are missing (in case config.py loaded too early)
                try:
                    from dotenv import load_dotenv
                    import os
                    # Try multiple paths for .env
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    # Navigate up to backend root (services -> app -> backend)
                    backend_dir = os.path.dirname(os.path.dirname(current_dir))
                    
                    env_paths = [
                        os.path.join(backend_dir, ".env"),
                        os.path.join(os.getcwd(), "backend", ".env"),
                        os.path.join(os.getcwd(), ".env")
                    ]
                    
                    logger.warning(f"Omise key missing. Checking paths: {env_paths}")
                    
                    for path in env_paths:
                        if os.path.exists(path):
                            logger.info(f"Loading .env from: {path}")
                            load_dotenv(dotenv_path=path, override=True)
                            break
                    
                    # Update settings instance with new values
                    new_secret = os.getenv("OMISE_SECRET_KEY", "").strip()
                    if new_secret:
                        settings.omise_secret_key = new_secret
                        settings.omise_public_key = os.getenv("OMISE_PUBLIC_KEY", "").strip()
                        logger.info("Successfully reloaded Omise keys from .env")
                    else:
                        logger.error("OMISE_SECRET_KEY still empty after reload")

                except Exception as reload_err:
                    logger.error(f"Failed to reload .env: {reload_err}")

            # Re-check after potential reload
            if not settings.omise_secret_key or not settings.omise_secret_key.startswith("skey_"):
                logger.error("Omise API keys not configured or invalid. Cannot process payment.")
                raise HTTPException(
                    status_code=500,
                    detail="Payment gateway configuration missing. Please configure OMISE_SECRET_KEY in .env file."
                )
            
            # Log test mode status
            is_test_mode = settings.omise_secret_key.startswith("skey_test_")
            if is_test_mode:
                logger.info("Using Omise TEST mode (sandbox) - Test cards can be used")
            else:
                logger.info("Using Omise LIVE mode - Real payments will be processed")
            
            async with httpx.AsyncClient() as client:
                # Try Links API first (if available)
                try:
                    response = await client.post(
                        "https://api.omise.co/links",
                        auth=(settings.omise_secret_key, ""),
                        json={
                            "amount": int(amount * 100),  # Convert to satang
                            "currency": currency.lower(),
                            "title": f"Booking #{booking_id}",
                            "description": f"Travel Booking Payment for {booking_id}"
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        link_data = response.json()
                        if "payment_uri" in link_data:
                            logger.info(f"Omise Links API successful: {link_data.get('id', 'N/A')}")
                            return link_data["payment_uri"]
                        else:
                            logger.warning(f"Omise Links response missing payment_uri: {link_data}")
                    elif response.status_code == 404:
                        logger.warning("Omise Links API not available (404). Account may need to activate Links feature in Dashboard.")
                    else:
                        error_text = response.text
                        logger.warning(f"Omise Links API error: {response.status_code} - {error_text}")
                        
                except httpx.RequestError as req_err:
                    logger.warning(f"Network error with Links API: {req_err}")
                except Exception as links_err:
                    logger.warning(f"Links API error: {links_err}")
                
                # Fallback: Use our own payment page with Omise.js
                logger.info("Using custom payment page with Omise.js integration")
                return_url = f"{settings.frontend_url}/bookings?booking_id={booking_id}&payment_status=success"
                cancel_url = f"{settings.frontend_url}/bookings?booking_id={booking_id}&payment_status=cancelled"
                
                # Use request base URL if provided, otherwise fallback to env or default
                try:
                    if request_base_url and str(request_base_url).strip():
                        backend_url = str(request_base_url).rstrip('/')
                    else:
                        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").strip()
                except Exception as url_err:
                    logger.warning(f"Error processing backend URL: {url_err}, using default")
                    backend_url = "http://localhost:8000"
                
                # URL encode parameters safely
                try:
                    from urllib.parse import quote
                    # We should NOT include & or = in safe characters, otherwise they will
                    # break the outer query string structure.
                    return_url_encoded = quote(return_url, safe='')
                    cancel_url_encoded = quote(cancel_url, safe='')
                except Exception as encode_err:
                    logger.warning(f"URL encoding failed, using raw URLs: {encode_err}")
                    return_url_encoded = return_url
                    cancel_url_encoded = cancel_url
                
                payment_page_url = f"{backend_url}/api/booking/payment-page/{booking_id}?amount={amount}&currency={currency}&return_url={return_url_encoded}&cancel_url={cancel_url_encoded}"
                logger.info(f"Returning payment page URL: {payment_page_url}")
                return payment_page_url
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create Omise checkout: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")
    
    @staticmethod
    async def create_checkout(booking_id: str, amount: float, currency: str = "THB", request_base_url: str = None) -> str:
        """
        Create Omise Checkout Session with Circuit Breaker protection
        
        Args:
            booking_id: Booking ID
            amount: Payment amount
            currency: Currency code (default: THB)
            request_base_url: Base URL from request (for payment page URL generation)
            
        Returns:
            Omise checkout URL
        """
        # Try the real service via Circuit Breaker
        try:
            return await omise_circuit_breaker.call(
                OmiseService._create_checkout_internal,
                booking_id,
                amount,
                currency,
                request_base_url
            )
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Omise request failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"Payment service unavailable: {str(e)}"
            )
