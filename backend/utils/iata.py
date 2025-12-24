from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from amadeus import Client as AmadeusClient
from amadeus import ResponseError


def normalize_place_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def is_iata3(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{3}", (s or "").strip()))


def retry(fn, tries: int = 3, base_sleep: float = 0.8):
    import time
    last = None
    for i in range(tries):
        try:
            return fn()
        except ResponseError as e:
            last = e
            code = getattr(e, "status_code", 0) or 0
            if code in (429, 500, 502, 503, 504):
                time.sleep(base_sleep * (2 ** i))
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(base_sleep * (2 ** i))
            continue
    raise last


def resolve_to_iata(
    amadeus_client: AmadeusClient,
    cache: Dict[str, str],
    text: Optional[str],
) -> Tuple[Optional[str], List[str]]:
    notes: List[str] = []
    if not text:
        return None, notes

    q = normalize_place_text(text)
    if not q:
        return None, notes

    if is_iata3(q):
        return q.upper(), notes

    ck = q.lower()
    if ck in cache:
        return cache[ck], notes

    def _search(subType: str):
        return amadeus_client.reference_data.locations.get(keyword=q, subType=subType, page={"limit": 10})

    # AIRPORT first
    try:
        r = retry(lambda: _search("AIRPORT"), tries=3)
        data = r.data or []
        if data:
            iata = (data[0] or {}).get("iataCode")
            if iata:
                cache[ck] = iata
                notes.append(f"resolved '{q}' -> {iata} (AIRPORT)")
                return iata, notes
    except Exception:
        pass

    # CITY second
    try:
        r = retry(lambda: _search("CITY"), tries=3)
        data = r.data or []
        if data:
            iata = (data[0] or {}).get("iataCode")
            if iata:
                cache[ck] = iata
                notes.append(f"resolved '{q}' -> {iata} (CITY)")
                return iata, notes
    except Exception:
        pass

    return None, notes
