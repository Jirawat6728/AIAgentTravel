from __future__ import annotations

import asyncio
import json
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from amadeus import Client as AmadeusClient
from amadeus import ResponseError

from core.config import AMADEUS_ENV, AMADEUS_HOST, get_amadeus_client
from core.slots import iso_date_or_none
from utils.iata import resolve_to_iata, retry

# =============================================================================
# Search Results schema helper
# =============================================================================
def empty_search_results() -> Dict[str, Any]:
    return {
        "flights": {"data": []},
        "hotels": {"data": []},
        "cars": {"data": []},
        "transport": {"data": []},
        "places": {"data": []},
        "booking": None,
    }


# =============================================================================
# Error helpers
# =============================================================================
def amadeus_error_payload(e: ResponseError) -> Dict[str, Any]:
    status = getattr(e, "status_code", None)
    body = None
    try:
        body = getattr(getattr(e, "response", None), "body", None)
    except Exception:
        body = None
    return {"status": status, "body": body, "desc": str(getattr(e, "description", ""))}


def is_invalid_client(error_payload: Dict[str, Any]) -> bool:
    try:
        body = (error_payload or {}).get("body") or {}
        s = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        return ("invalid_client" in s) or (isinstance(body, dict) and body.get("error") == "invalid_client")
    except Exception:
        return False


# =============================================================================
# Hotels v3 (stable): by_city -> hotelIds -> hotel-offers (hotelIds required)
# =============================================================================
def date_shift_candidates(check_in: str, nights: int, shifts: List[int]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    base = date.fromisoformat(check_in)
    for s in shifts:
        ci = (base + timedelta(days=s)).isoformat()
        co = (base + timedelta(days=s + nights)).isoformat()
        out.append((ci, co))
    return out


def hotel_ids_by_city(client: AmadeusClient, city_code: str, limit: int = 25) -> List[str]:
    resp = retry(lambda: client.reference_data.locations.hotels.by_city.get(cityCode=city_code), tries=3)
    data = resp.data or []
    ids: List[str] = []
    for h in data:
        hid = (h or {}).get("hotelId")
        if hid:
            ids.append(hid)
    return ids[:limit]


def hotel_offers_v3(
    client: AmadeusClient,
    hotel_ids: List[str],
    check_in: str,
    check_out: str,
    adults: int,
    room_qty: int = 1,
) -> List[Dict[str, Any]]:
    ids = [x for x in (hotel_ids or []) if x]
    if not ids:
        return []
    params: Dict[str, Any] = {
        "hotelIds": ",".join(ids),
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": str(adults),
        "roomQuantity": str(room_qty),
    }
    resp = retry(lambda: client.shopping.hotel_offers_search.get(**params), tries=3)
    return resp.data or []


def hotel_search_stable_v3(
    client: AmadeusClient,
    primary_city_code: str,
    check_in: str,
    nights: int,
    adults: int,
    fallback_city_codes: Optional[List[str]] = None,
    shifts: Optional[List[int]] = None,
    hotel_ids_limit: int = 25,
    time_budget_sec: float = 35.0,
) -> Dict[str, Any]:
    """
    time_budget_sec: hard-ish time budget for the hotel search in a single request.
    Keeps the overall /api/chat under ~1 minute when combined with flights/cars.
    """
    if shifts is None:
        shifts = [0, 1, -1, 2, -2, 3, -3, 5, -5]

    start_t = time.monotonic()
    cities = [primary_city_code] + [c for c in (fallback_city_codes or []) if c and c != primary_city_code]
    debug: Dict[str, Any] = {"attempts": [], "picked": None}

    for city in cities:
        if time.monotonic() - start_t > time_budget_sec:
            debug["attempts"].append({"step": "hotel_time_budget_exceeded", "cityCode": city})
            break

        try:
            ids = hotel_ids_by_city(client, city_code=city, limit=hotel_ids_limit)
            debug["attempts"].append({"step": "hotel_ids_by_city", "cityCode": city, "count": len(ids)})
        except ResponseError as e:
            debug["attempts"].append({"step": "hotel_ids_by_city", "cityCode": city, "error": amadeus_error_payload(e)})
            continue
        except Exception as e:
            debug["attempts"].append({"step": "hotel_ids_by_city", "cityCode": city, "error": {"status": 500, "message": str(e)}})
            continue

        if not ids:
            continue

        for ci, co in date_shift_candidates(check_in, nights, shifts):
            if time.monotonic() - start_t > time_budget_sec:
                debug["attempts"].append({"step": "hotel_time_budget_exceeded", "cityCode": city})
                break

            try:
                offers = hotel_offers_v3(
                    client,
                    hotel_ids=ids[:10],
                    check_in=ci,
                    check_out=co,
                    adults=adults,
                    room_qty=1,
                )
                debug["attempts"].append(
                    {"step": "hotel_offers_v3", "cityCode": city, "checkInDate": ci, "checkOutDate": co, "count": len(offers)}
                )
                if offers:
                    debug["picked"] = {"cityCode": city, "checkInDate": ci, "checkOutDate": co}
                    return {"ok": True, "offers": offers, "picked": debug["picked"], "debug": debug}
            except ResponseError as e:
                debug["attempts"].append({"step": "hotel_offers_v3", "cityCode": city, "checkInDate": ci, "checkOutDate": co, "error": amadeus_error_payload(e)})
                continue
            except Exception as e:
                debug["attempts"].append({"step": "hotel_offers_v3", "cityCode": city, "checkInDate": ci, "checkOutDate": co, "error": {"status": 500, "message": str(e)}})
                continue

    return {"ok": False, "offers": [], "picked": None, "debug": debug, "reason": "no_offers_in_env"}


# =============================================================================
# Concurrent fetch: flights + hotels + cars
#   - Amadeus SDK is sync => use asyncio.to_thread
#   - hard overall timeout so response comes back within ~1 minute
# =============================================================================
def _search_flights(
    client: AmadeusClient,
    origin_air: str,
    dest_air: str,
    start_date: str,
    adults: int,
    children: int,
) -> Dict[str, Any]:
    flight_kwargs: Dict[str, Any] = {
        "originLocationCode": origin_air,
        "destinationLocationCode": dest_air,
        "departureDate": start_date,
        "adults": adults,
        "max": 20,
    }
    if children > 0:
        flight_kwargs["children"] = children

    resp = retry(lambda: client.shopping.flight_offers_search.get(**flight_kwargs), tries=3)
    return {"data": resp.data or [], "kwargs": flight_kwargs}


def _search_hotels(
    client: AmadeusClient,
    dest_air: str,
    start_date: str,
    nights: int,
    adults: int,
    time_budget_sec: float = 35.0,
) -> Dict[str, Any]:
    # Practical fallback for TEST env (some cities have 0 offers)
    fallback_hotels: List[str] = []
    if dest_air == "KBV":
        fallback_hotels = ["HKT", "BKK"]
    else:
        fallback_hotels = ["BKK"]

    pack = hotel_search_stable_v3(
        client=client,
        primary_city_code=dest_air,
        check_in=start_date,
        nights=nights,
        adults=adults,
        fallback_city_codes=fallback_hotels,
        time_budget_sec=time_budget_sec,
    )
    return {"offers": pack.get("offers") or [], "picked": pack.get("picked"), "debug": pack.get("debug"), "ok": bool(pack.get("ok"))}


def _search_cars(
    client: AmadeusClient,
    dest_air: str,
    start_date: str,
    nights: int,
) -> Dict[str, Any]:
    """
    Car inventory in Self-Service sandbox can be sparse.
    We try, but never fail the whole request.
    """
    pickup = start_date
    dropoff = (date.fromisoformat(start_date) + timedelta(days=max(1, nights))).isoformat()

    # The SDK endpoint name varies; we guard with getattr chain.
    try:
        shopping = getattr(client, "shopping", None)
        car_ep = getattr(shopping, "car_rental_offers", None)
        if not car_ep or not hasattr(car_ep, "get"):
            return {"data": [], "note": "car endpoint not available in this SDK/version"}

        params = {
            "pickupLocation": dest_air,
            "pickupDate": pickup,
            "dropoffDate": dropoff,
        }
        resp = retry(lambda: car_ep.get(**params), tries=2)
        return {"data": resp.data or [], "kwargs": params}
    except ResponseError as e:
        return {"data": [], "error": amadeus_error_payload(e)}
    except Exception as e:
        return {"data": [], "error": {"status": 500, "message": str(e)}}


async def amadeus_search_async(
    travel_slots: Dict[str, Any],
    user_iata_cache: Dict[str, str],
    overall_timeout_sec: float = 55.0,
) -> Dict[str, Any]:
    """
    Goal:
      - return something within ~1 minute (overall_timeout_sec default 55s)
      - fetch flights/hotels/cars in parallel
      - never hallucinate; pass through Amadeus data only
    """
    origin_txt = travel_slots.get("origin")
    dest_txt = travel_slots.get("destination")

    start_date = iso_date_or_none(travel_slots.get("start_date"))
    nights = int(travel_slots.get("nights") or 3)
    adults = int(travel_slots.get("adults") or 2)
    children = int(travel_slots.get("children") or 0)

    client = get_amadeus_client()
    if not client:
        return {
            "ok": False,
            "error": {"status": 400, "body": {"message": "AMADEUS_API_KEY/AMADEUS_API_SECRET not set in .env"}},
            "debug": {"env": AMADEUS_ENV, "host": AMADEUS_HOST, "slots_in": travel_slots},
            "search_results": empty_search_results(),
        }

    # Validate dates quickly
    if not start_date:
        return {"ok": False, "error": {"status": 422, "body": {"message": "invalid/missing start_date"}}, "debug": {"slots_in": travel_slots}, "search_results": empty_search_results()}
    try:
        start_dt = date.fromisoformat(start_date)
        if start_dt < date.today():
            return {"ok": False, "error": {"status": 422, "body": {"message": "start_date is in the past"}}, "debug": {"slots_in": travel_slots}, "search_results": empty_search_results()}
    except Exception:
        return {"ok": False, "error": {"status": 422, "body": {"message": "invalid start_date format"}}, "debug": {"slots_in": travel_slots}, "search_results": empty_search_results()}

    # Resolve IATA (sync but fast) in thread to not block event loop
    origin_air, notes1 = await asyncio.to_thread(resolve_to_iata, client, user_iata_cache, origin_txt)
    dest_air, notes2 = await asyncio.to_thread(resolve_to_iata, client, user_iata_cache, dest_txt)

    debug: Dict[str, Any] = {
        "env": AMADEUS_ENV,
        "host": AMADEUS_HOST,
        "slots_in": travel_slots,
        "origin_txt": origin_txt,
        "dest_txt": dest_txt,
        "origin_air": origin_air,
        "dest_air": dest_air,
        "notes": notes1 + notes2,
    }

    if not origin_air or not dest_air:
        return {
            "ok": False,
            "error": {"status": 422, "body": {"message": "could not resolve origin/destination to IATA (ref-data returned none)"}},
            "debug": debug,
            "search_results": empty_search_results(),
        }

    debug["return_date"] = (start_dt + timedelta(days=nights)).isoformat()

    async def _run_with_tag(tag: str, coro):
        t0 = time.monotonic()
        try:
            res = await coro
            return tag, res, round(time.monotonic() - t0, 3), None
        except Exception as e:
            return tag, None, round(time.monotonic() - t0, 3), str(e)

    flights_task = _run_with_tag(
        "flights",
        asyncio.to_thread(_search_flights, client, origin_air, dest_air, start_date, adults, children),
    )
    hotels_task = _run_with_tag(
        "hotels",
        asyncio.to_thread(_search_hotels, client, dest_air, start_date, nights, adults, 35.0),
    )
    cars_task = _run_with_tag(
        "cars",
        asyncio.to_thread(_search_cars, client, dest_air, start_date, nights),
    )

    try:
        results = await asyncio.wait_for(asyncio.gather(flights_task, hotels_task, cars_task), timeout=overall_timeout_sec)
    except asyncio.TimeoutError:
        # Partial timeout: return whatever finished via wait()
        # We re-run using asyncio.wait to collect done tasks quickly.
        pending = {asyncio.create_task(flights_task), asyncio.create_task(hotels_task), asyncio.create_task(cars_task)}
        done, pending = await asyncio.wait(pending, timeout=0.0)
        debug["parallel_timeout"] = True
        debug["overall_timeout_sec"] = overall_timeout_sec
        results = [d.result() for d in done]  # type: ignore
        for p in pending:
            p.cancel()

    timings: Dict[str, Any] = {}
    flights_data: List[Dict[str, Any]] = []
    hotels_data: List[Dict[str, Any]] = []
    cars_data: List[Dict[str, Any]] = []
    hotel_pack_picked = None
    hotel_debug = None
    flight_kwargs = None

    for tag, res, sec, err in results:
        timings[tag] = {"seconds": sec, "error": err}
        if tag == "flights" and res:
            flights_data = (res.get("data") or [])
            flight_kwargs = res.get("kwargs")
        elif tag == "hotels" and res:
            hotels_data = (res.get("offers") or [])
            hotel_pack_picked = res.get("picked")
            hotel_debug = res.get("debug")
        elif tag == "cars" and res:
            cars_data = (res.get("data") or [])

    debug["timings"] = timings
    if flight_kwargs:
        debug["flight_kwargs"] = flight_kwargs
    debug["hotel_pack"] = hotel_pack_picked
    debug["hotel_debug"] = hotel_debug

    search_results = {
        "flights": {"data": flights_data},
        "hotels": {"data": hotels_data},
        "cars": {"data": cars_data},
        "transport": {"data": []},
        "places": {"data": []},
        "booking": None,
    }
    return {"ok": True, "error": None, "debug": debug, "search_results": search_results}
