# main.py
# ============================================================
# AI Travel Agent – Gemini CLI = 100% LLM Agent (Stateful)
# Backend = tool runner only (Amadeus ref-data + search + plan builder)
#
# Requirements:
#   pip install fastapi uvicorn python-dotenv amadeus
#   npm i -g @google/gemini-cli
#
# .env (backend folder):
#   GEMINI_API_KEY=...
#   GEMINI_MODEL_NAME=gemini-flash-latest
#   GEMINI_CLI_BIN=gemini   # or full path to gemini.cmd
#   AMADEUS_API_KEY=...
#   AMADEUS_API_SECRET=...
#   AMADEUS_ENV=test
#
# Run:
#   uvicorn main:app --reload --host 127.0.0.1 --port 8000
# ============================================================

from __future__ import annotations

import os
import json
import time
import shutil
import subprocess
import traceback
from datetime import date, timedelta
from typing import Any, Dict, Optional, List, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from amadeus import Client as AmadeusClient, ResponseError


# ============================================================
# 0) ENV / Clients
# ============================================================
load_dotenv(override=True)

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

GEMINI_MODEL_NAME = (os.getenv("GEMINI_MODEL_NAME") or "gemini-flash-latest").strip()
GEMINI_CLI_BIN_ENV = (os.getenv("GEMINI_CLI_BIN") or "gemini").strip()

AMADEUS_API_KEY = (os.getenv("AMADEUS_API_KEY") or "").strip()
AMADEUS_API_SECRET = (os.getenv("AMADEUS_API_SECRET") or "").strip()
AMADEUS_ENV = (os.getenv("AMADEUS_ENV") or "test").strip().lower()
if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
    raise RuntimeError("AMADEUS_API_KEY/AMADEUS_API_SECRET not set in .env")

AMADEUS_HOST = "test" if AMADEUS_ENV == "test" else "production"

amadeus = AmadeusClient(
    client_id=AMADEUS_API_KEY,
    client_secret=AMADEUS_API_SECRET,
    hostname=AMADEUS_HOST,
)


# ============================================================
# 0.1) Stateful per-user memory (in-memory)
# ============================================================
USER_CONTEXTS: Dict[str, Dict[str, Any]] = {}


def get_user_ctx(user_id: str) -> Dict[str, Any]:
    ctx = USER_CONTEXTS.get(user_id)
    if not ctx:
        ctx = {
            "slots": {},                 # agent-owned slots
            "plan_choices": [],
            "current_plan": None,
            "last_search_results": None,
            "history": [],               # for stateful agent
            "summary": "",
        }
        USER_CONTEXTS[user_id] = ctx
    return ctx


def empty_search_results() -> Dict[str, Any]:
    return {
        "flights": {"data": [], "dictionaries": None},
        "hotels": {"data": []},
        "cars": {"data": []},
        "transport": {"data": []},
        "places": {"data": []},
        "booking": None,
    }


# ============================================================
# 1) Gemini CLI runner (fallback + where.exe log)
# ============================================================
class GeminiCLLError(RuntimeError):
    pass


def where_gemini_debug() -> Dict[str, Any]:
    dbg: Dict[str, Any] = {"env_bin": GEMINI_CLI_BIN_ENV, "which": None, "where": None}
    try:
        dbg["which"] = shutil.which("gemini")
    except Exception as e:
        dbg["which"] = f"ERR: {e}"

    if os.name == "nt":
        try:
            p = subprocess.run(["where.exe", "gemini"], text=True, capture_output=True, timeout=3, check=False)
            dbg["where"] = {"rc": p.returncode, "stdout": (p.stdout or "").strip(), "stderr": (p.stderr or "").strip()}
        except Exception as e:
            dbg["where"] = f"ERR: {e}"
    return dbg


def locate_gemini_cli() -> Tuple[Optional[str], Dict[str, Any]]:
    dbg = where_gemini_debug()

    envp = (GEMINI_CLI_BIN_ENV or "").strip().strip('"')
    if envp:
        # if path-like, validate
        if (os.path.sep in envp) or envp.lower().endswith((".cmd", ".exe", ".bat")):
            if os.path.exists(envp):
                return envp, {**dbg, "picked": "env_path"}
        else:
            w = shutil.which(envp)
            if w:
                return w, {**dbg, "picked": "env_name"}

    w = shutil.which("gemini")
    if w:
        return w, {**dbg, "picked": "which_gemini"}

    # last resort on Windows: first output from where.exe
    if os.name == "nt" and isinstance(dbg.get("where"), dict):
        lines = [x.strip() for x in (dbg["where"].get("stdout") or "").splitlines() if x.strip()]
        if lines:
            return lines[0], {**dbg, "picked": "where_first"}

    return None, {**dbg, "picked": None}


def safe_extract_json(text: str) -> Optional[dict]:
    try:
        raw = (text or "").strip()
        # strip markdown fences if any
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].strip()
        # take outermost object
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]
        return json.loads(raw)
    except Exception:
        return None


def gemini_cli(prompt: str, *, model: str, timeout_s: int = 120) -> str:
    exe, exe_dbg = locate_gemini_cli()
    if not exe:
        raise GeminiCLLError(f"Gemini CLI not found. Set GEMINI_CLI_BIN or fix PATH.\n{json.dumps(exe_dbg, ensure_ascii=False)}")

    cmd = [exe, "--model", model, "-p", prompt]

    env = os.environ.copy()
    env["GEMINI_API_KEY"] = GEMINI_API_KEY
    env.setdefault("GOOGLE_API_KEY", GEMINI_API_KEY)
    env.setdefault("CI", "1")
    env.setdefault("NO_COLOR", "1")
    env["GEMINI_SANDBOX"] = "false"

    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s, check=False, env=env)
    except subprocess.TimeoutExpired as e:
        raise GeminiCLLError(f"Gemini CLI timeout after {timeout_s}s\n{json.dumps(exe_dbg, ensure_ascii=False)}") from e
    except FileNotFoundError as e:
        raise GeminiCLLError(f"Gemini CLI FileNotFoundError\nexe={exe}\n{json.dumps(exe_dbg, ensure_ascii=False)}") from e

    if p.returncode != 0:
        raise GeminiCLLError(
            "Gemini CLI failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"rc: {p.returncode}\n"
            f"stderr: {(p.stderr or '')[-2000:]}\n"
            f"exe_debug: {json.dumps(exe_dbg, ensure_ascii=False)}"
        )

    out = (p.stdout or "").strip()
    if not out:
        raise GeminiCLLError("Gemini CLI returned empty output")
    return out


# ============================================================
# 2) Agent prompts (100% agent-owned behavior)
# ============================================================
AGENT_SYSTEM = r"""
You are a STATEFUL Thai travel agent.
You control EVERYTHING: slot extraction, routing, decisions, and final response.

ABSOLUTE RULES:
- Output ONLY ONE valid JSON object. No markdown. No extra text.
- NEVER ask the user to provide airport/IATA codes.
- Be autonomous: infer missing details; if truly ambiguous, choose a sensible default and proceed.
- DO NOT invent prices. Use only prices in the provided search_results / plan_choices.
- Be concise, helpful, Thai natural.

SLOTS (agent-owned):
{
  "origin": "string|null",          // city/airport name
  "destination": "string|null",
  "route": ["string", ...] | null,  // optional, e.g. ["Bangkok","Tokyo","Seoul"]
  "start_date": "YYYY-MM-DD|null",
  "nights": number|null,
  "adults": number|null,
  "children": number|null
}

TOOLS AVAILABLE (backend will run based on actions):
- resolve_locations: needs origin/destination (strings) -> returns IATA + hotel_city_code
- search_amadeus: needs resolved codes + dates + pax -> returns flights+hotels

ACTIONS FORMAT (in "decide" mode):
{"type":"resolve_locations"} or {"type":"search_amadeus"} or {"type":"none"}

You must follow 2-step protocol:
Mode "decide":
{
  "mode":"decide",
  "slots_update": { ...partial slots... },
  "actions":[...],
  "assistant_thought":"string short",
  "memory_update":"string optional"
}

Mode "respond":
{
  "mode":"respond",
  "response":"string Thai",
  "suggestions":["..."],
  "memory_update":"string optional"
}

When plan_choices exist, invite user to "เลือกช้อยส์ X".
"""

SUMMARIZER_SYSTEM = r"""
Output JSON only: {"summary":"..."}.
Summarize stable preferences & constraints from history (Thai). Short.
"""


def build_agent_prompt(*, system: str, summary: str, history: List[Dict[str, str]], context: Dict[str, Any], user_message: str) -> str:
    h = (history or [])[-16:]
    parts: List[str] = []
    parts.append("SYSTEM:\n" + system.strip())
    if summary:
        parts.append("\nMEMORY_SUMMARY:\n" + summary.strip())
    if h:
        parts.append("\nHISTORY:")
        for m in h:
            r = (m.get("role") or "user").upper()
            c = (m.get("content") or "").strip()
            if c:
                parts.append(f"{r}: {c}")
    parts.append("\nCONTEXT_JSON:\n" + json.dumps(context or {}, ensure_ascii=False))
    parts.append("\nUSER:\n" + (user_message or "").strip())
    parts.append("\nABSOLUTE: Output ONLY one JSON object.")
    return "\n".join(parts)


def maybe_summarize(user_id: str) -> None:
    ctx = get_user_ctx(user_id)
    hist = ctx.get("history") or []
    if len(hist) < 50:
        return

    prompt = build_agent_prompt(
        system=SUMMARIZER_SYSTEM,
        summary=ctx.get("summary") or "",
        history=[],
        context={"history": hist[-50:]},
        user_message="สรุป memory",
    )
    raw = gemini_cli(prompt, model=GEMINI_MODEL_NAME, timeout_s=60)
    data = safe_extract_json(raw)
    s = (data or {}).get("summary") if isinstance(data, dict) else None
    if isinstance(s, str) and s.strip():
        base = (ctx.get("summary") or "").strip()
        ctx["summary"] = (base + "\n" + s.strip()).strip()
    ctx["history"] = hist[-10:]
    USER_CONTEXTS[user_id] = ctx


def agent_call(user_id: str, *, mode: str, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    maybe_summarize(user_id)
    ctx = get_user_ctx(user_id)

    prompt = build_agent_prompt(
        system=AGENT_SYSTEM,
        summary=ctx.get("summary") or "",
        history=ctx.get("history") or [],
        context={**(context or {}), "mode": mode},
        user_message=user_message,
    )
    raw = gemini_cli(prompt, model=GEMINI_MODEL_NAME, timeout_s=120)
    data = safe_extract_json(raw)
    if not isinstance(data, dict):
        return {"mode": mode, "response": "ขออภัยค่ะ ระบบประมวลผลไม่สำเร็จ ลองใหม่อีกครั้งนะคะ", "suggestions": []}
    return data


def push_history(user_id: str, role: str, content: str) -> None:
    ctx = get_user_ctx(user_id)
    hist = ctx.get("history") or []
    hist.append({"role": role, "content": content})
    ctx["history"] = hist[-80:]
    USER_CONTEXTS[user_id] = ctx


def apply_memory_update(user_id: str, s: Any) -> None:
    if not isinstance(s, str) or not s.strip():
        return
    ctx = get_user_ctx(user_id)
    base = (ctx.get("summary") or "").strip()
    ctx["summary"] = (base + "\n" + s.strip()).strip()
    USER_CONTEXTS[user_id] = ctx


# ============================================================
# 3) Amadeus tools (ref-data resolve + search) + retry
# ============================================================
RETRY_STATUSES = {429, 500, 502, 503, 504}


def amadeus_call(fn, *, tries: int = 3, base_sleep: float = 0.6):
    last = None
    for i in range(tries):
        try:
            return fn()
        except ResponseError as e:
            last = e
            status = getattr(e, "status_code", None)
            if status in RETRY_STATUSES and i < tries - 1:
                time.sleep(base_sleep * (2 ** i))
                continue
            raise
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(base_sleep * (2 ** i))
                continue
            raise
    if last:
        raise last
    raise RuntimeError("amadeus_call failed")


def score_loc(item: Dict[str, Any]) -> float:
    # simple: prefer AIRPORT > CITY, then travelers score
    st = (item.get("subType") or "").upper()
    sc = 0.0
    if st == "AIRPORT":
        sc += 2.0
    elif st == "CITY":
        sc += 1.0
    t = ((item.get("analytics") or {}).get("travelers") or {}).get("score")
    try:
        sc += float(t or 0)
    except Exception:
        pass
    return sc


def resolve_location_iata(query: str, subtypes: str) -> Tuple[Optional[str], Dict[str, Any]]:
    if not query:
        return None, {"reason": "empty"}
    if isinstance(query, str) and len(query.strip()) == 3 and query.strip().isalpha():
        return query.strip().upper(), {"reason": "looks_like_iata"}

    resp = amadeus_call(lambda: amadeus.reference_data.locations.get(keyword=query, subType=subtypes))
    data = resp.data or []
    if not data:
        return None, {"reason": "no_results"}

    best = max(data[:10], key=score_loc)
    code = best.get("iataCode")
    if isinstance(code, str) and len(code) == 3:
        return code.upper(), {"picked": {"iataCode": code, "name": best.get("name"), "subType": best.get("subType"), "address": best.get("address")}}
    return None, {"reason": "no_iataCode"}


def resolve_hotel_city_code(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    # Prefer CITY subtype for hotels
    code, dbg = resolve_location_iata(query, subtypes="CITY")
    if code:
        return code, {"city_only": dbg}
    code2, dbg2 = resolve_location_iata(query, subtypes="CITY,AIRPORT")
    return code2, {"city_only": dbg, "fallback": dbg2}


def hotel_2step(city_code: str, check_in: str, check_out: str, adults: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    dbg = {"step1_count": 0, "hotelIds_used": 0, "step2_count": 0}
    resp_list = amadeus_call(lambda: amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code))
    lst = resp_list.data or []
    dbg["step1_count"] = len(lst)

    ids = []
    for x in lst[:30]:
        hid = x.get("hotelId")
        if hid:
            ids.append(hid)
    dbg["hotelIds_used"] = len(ids)
    if not ids:
        return [], dbg

    resp_offers = amadeus_call(
        lambda: amadeus.shopping.hotel_offers_search.get(
            hotelIds=",".join(ids),
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=adults,
            roomQuantity=1,
        )
    )
    offers = resp_offers.data or []
    dbg["step2_count"] = len(offers)
    return offers, dbg


def amadeus_search(*, origin_iata: str, dest_iata: str, hotel_city_code: str, start_date: str, nights: int, adults: int, children: int) -> Dict[str, Any]:
    start_dt = date.fromisoformat(start_date)
    return_date = (start_dt + timedelta(days=int(nights))).isoformat()

    # flights (roundtrip for stability)
    flight_kwargs = {
        "originLocationCode": origin_iata,
        "destinationLocationCode": dest_iata,
        "departureDate": start_date,
        "returnDate": return_date,
        "adults": int(adults),
        "max": 20,
        "currencyCode": "THB",
    }
    if int(children) > 0:
        flight_kwargs["children"] = int(children)

    resp_f = amadeus_call(lambda: amadeus.shopping.flight_offers_search.get(**flight_kwargs))
    flights = resp_f.data or []
    dictionaries = None
    try:
        dictionaries = (resp_f.result or {}).get("dictionaries")
    except Exception:
        dictionaries = None

    # hotels (2-step)
    hotels, hdbg = hotel_2step(hotel_city_code, check_in=start_date, check_out=return_date, adults=int(adults))

    return {
        "ok": True,
        "debug": {"flight_kwargs": flight_kwargs, "return_date": return_date, "hotel_2step": hdbg},
        "search_results": {
            "flights": {"data": flights, "dictionaries": dictionaries},
            "hotels": {"data": hotels},
            "cars": {"data": []},
            "transport": {"data": []},
            "places": {"data": []},
            "booking": None,
        },
    }


# ============================================================
# 4) Plan builder (simple + stable)
# ============================================================
def pick_flight_fields(f: Dict[str, Any], dictionaries: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    dict_carriers = (dictionaries or {}).get("carriers") or {}

    price = 0.0
    try:
        price = float((f.get("price") or {}).get("grandTotal") or (f.get("price") or {}).get("total") or 0)
    except Exception:
        price = 0.0

    itin = (f.get("itineraries") or [{}])[0]
    segs = itin.get("segments") or []
    first = segs[0] if segs else {}
    last = segs[-1] if segs else {}

    carrier = first.get("carrierCode") or "XX"
    airline = dict_carriers.get(carrier, carrier)
    num = first.get("number") or ""
    origin = ((first.get("departure") or {}).get("iataCode")) or "UNK"
    dest = ((last.get("arrival") or {}).get("iataCode")) or "UNK"

    return {
        "airline": airline,
        "carrier_code": carrier,
        "flight_number": f"{carrier}{num}".strip(),
        "origin": origin,
        "destination": dest,
        "departure_time": (first.get("departure") or {}).get("at", ""),
        "arrival_time": (last.get("arrival") or {}).get("at", ""),
        "stops": max(0, len(segs) - 1),
        "duration": itin.get("duration"),
        "flight_price": price,
    }


def pick_hotel_fields(h: Dict[str, Any]) -> Dict[str, Any]:
    hotel = h.get("hotel") or {}
    name = h.get("name") or hotel.get("name") or "Unknown Hotel"
    city = (hotel.get("address") or {}).get("cityName") or h.get("cityCode") or "Unknown"

    price = 0.0
    cur = None
    try:
        offers = h.get("offers") or []
        if offers:
            p = offers[0].get("price") or {}
            cur = p.get("currency")
            price = float(p.get("total") or 0)
    except Exception:
        pass

    return {"name": name, "location": city, "hotel_price": price, "hotel_currency": cur}


def build_plan_choices_10(search_results: Dict[str, Any], nights: int) -> List[Dict[str, Any]]:
    flights = ((search_results.get("flights") or {}).get("data")) or []
    hotels = ((search_results.get("hotels") or {}).get("data")) or []
    if not flights or not hotels:
        return []

    dicts = (search_results.get("flights") or {}).get("dictionaries") or {}
    out: List[Dict[str, Any]] = []

    for i in range(10):
        f = flights[i % len(flights)]
        h = hotels[i % len(hotels)]
        ff = pick_flight_fields(f, dicts)
        hh = pick_hotel_fields(h)

        fp = float(ff.get("flight_price") or 0)
        hp = float(hh.get("hotel_price") or 0)
        total = (fp + hp) if (fp > 0 or hp > 0) else 0.0
        cur = hh.get("hotel_currency") or "THB"

        out.append(
            {
                "id": i + 1,
                "label": f"ช้อยส์ {i+1}",
                "recommended": False,
                "tags": ["Amadeus", "ราคาจากผลลัพธ์จริง"],
                "flight": {
                    "airline": ff["airline"],
                    "flight_number": ff["flight_number"],
                    "origin": ff["origin"],
                    "destination": ff["destination"],
                    "departure_time": ff["departure_time"],
                    "arrival_time": ff["arrival_time"],
                    "stops": ff["stops"],
                    "duration": ff["duration"],
                },
                "hotel": {"name": hh["name"], "location": hh["location"], "nights": int(nights)},
                "currency": cur,
                "total_price": round(total) if total > 0 else None,
                "price_breakdown": {
                    "flight_total": round(fp) if fp > 0 else None,
                    "hotel_total": round(hp) if hp > 0 else None,
                    "currency": cur,
                },
            }
        )

    priced = [c for c in out if isinstance(c.get("total_price"), int)]
    if priced:
        priced.sort(key=lambda x: x["total_price"])
        cheapest = priced[0]
        ordered = [cheapest] + [c for c in out if c is not cheapest]
        for idx, c in enumerate(ordered, start=1):
            c["id"] = idx
            c["label"] = f"ช้อยส์ {idx}"
            c["recommended"] = (idx == 1)
        return ordered

    out[0]["recommended"] = True
    return out


# ============================================================
# 5) Choice select
# ============================================================
def parse_choice_selection(msg: str) -> Optional[int]:
    import re
    m = re.search(r"(?:เลือกช้อยส์|เลือก\s*ช้อยส์|เลือก)\s*(\d+)", msg or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def handle_choice_select(user_id: str, choice_id: int) -> Dict[str, Any]:
    ctx = get_user_ctx(user_id)
    plans = ctx.get("plan_choices") or []
    if not plans:
        return {
            "response": "ตอนนี้ยังไม่มีช้อยส์ให้เลือกค่ะ ลองพิมพ์แผนทริปอีกครั้ง แล้วฉันจะค้นหาให้อัตโนมัติค่ะ ✅",
            "travel_slots": ctx.get("slots") or {},
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": None,
            "suggestions": ["เชียงใหม่ไปกระบี่ 26 ธ.ค. 4 คืน ผู้ใหญ่ 2 เด็ก 1"],
            "debug": {},
        }

    chosen = next((p for p in plans if int(p.get("id", -1)) == int(choice_id)), None)
    if not chosen:
        return {
            "response": f"ไม่พบช้อยส์ {choice_id} ในรายการล่าสุดค่ะ ลองเลือก 1–10 ใหม่อีกครั้งนะคะ",
            "travel_slots": ctx.get("slots") or {},
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,
            "current_plan": None,
            "suggestions": ["เลือกช้อยส์ 1", "เลือกช้อยส์ 2", "เลือกช้อยส์ 3"],
            "debug": {},
        }

    ctx["current_plan"] = chosen
    USER_CONTEXTS[user_id] = ctx
    return {
        "response": f"รับทราบค่ะ ✅ เลือกช้อยส์ {choice_id} แล้ว\nอยากให้ปรับอะไรต่อคะ (ไฟลต์/ที่พัก/จำนวนคืน)?",
        "travel_slots": ctx.get("slots") or {},
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": plans,
        "current_plan": chosen,
        "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักใกล้ทะเล", "ปรับจำนวนคืน", "โอเค ยืนยันแพลนนี้"],
        "debug": {},
    }


# ============================================================
# 6) Orchestrator (Agent 100%)
# ============================================================
def orchestrate_chat(user_id: str, user_message: str) -> Dict[str, Any]:
    ctx = get_user_ctx(user_id)

    # choice shortcut
    cid = parse_choice_selection(user_message)
    if cid is not None:
        out = handle_choice_select(user_id, cid)
        push_history(user_id, "user", user_message)
        push_history(user_id, "assistant", out.get("response", ""))
        return out

    # agent decides (slots + actions)
    decide_context = {
        "today": date.today().isoformat(),
        "slots": ctx.get("slots") or {},
        "current_plan": ctx.get("current_plan"),
        "have_plan_choices": bool(ctx.get("plan_choices")),
        "amadeus_env": AMADEUS_ENV,
        "policy": {
            "agent_is_100_percent_owner": True,
            "never_ask_iata": True,
            "be_autonomous": True,
        },
    }
    dec = agent_call(user_id, mode="decide", user_message=user_message, context=decide_context)

    slots_update = dec.get("slots_update") if isinstance(dec, dict) else None
    if not isinstance(slots_update, dict):
        slots_update = {}

    # merge slots (agent-owned)
    slots = dict(ctx.get("slots") or {})
    slots.update({k: v for k, v in slots_update.items() if v is not None})
    ctx["slots"] = slots

    actions = dec.get("actions") if isinstance(dec, dict) else None
    if not isinstance(actions, list) or not actions:
        actions = [{"type": "resolve_locations"}, {"type": "search_amadeus"}]

    debug_tools: Dict[str, Any] = {"actions": actions, "resolve": None, "search": None}
    tool_data = {"resolved": None, "search": None, "plan_choices": None}

    # execute actions
    origin = slots.get("origin")
    destination = slots.get("destination")
    route = slots.get("route")
    if isinstance(route, list) and len(route) >= 2:
        origin = origin or route[0]
        destination = destination or route[-1]

    # minimal safety defaults if agent omitted (but not asking user)
    # (agent still "owns" behavior; this just prevents crashes)
    start_date = slots.get("start_date") or (date.today() + timedelta(days=1)).isoformat()
    nights = int(slots.get("nights") or 3)
    adults = int(slots.get("adults") or 2)
    children = int(slots.get("children") or 0)

    resolved = None
    for a in actions:
        at = (a or {}).get("type") if isinstance(a, dict) else None

        if at == "resolve_locations":
            try:
                oi, odbg = resolve_location_iata(str(origin or ""), subtypes="CITY,AIRPORT")
                di, ddbg = resolve_location_iata(str(destination or ""), subtypes="CITY,AIRPORT")
                hc, hdbg = resolve_hotel_city_code(str(destination or ""))
                resolved = {
                    "origin_iata": oi,
                    "dest_iata": di,
                    "hotel_city_code": hc,
                    "debug": {"origin": odbg, "destination": ddbg, "hotel_city": hdbg},
                }
                debug_tools["resolve"] = resolved
                tool_data["resolved"] = resolved
            except Exception as e:
                debug_tools["resolve"] = {"error": str(e)}
                resolved = None

        if at == "search_amadeus":
            if not resolved:
                # try resolve implicitly
                try:
                    oi, _ = resolve_location_iata(str(origin or ""), subtypes="CITY,AIRPORT")
                    di, _ = resolve_location_iata(str(destination or ""), subtypes="CITY,AIRPORT")
                    hc, _ = resolve_hotel_city_code(str(destination or ""))
                    resolved = {"origin_iata": oi, "dest_iata": di, "hotel_city_code": hc, "debug": {}}
                    tool_data["resolved"] = resolved
                except Exception:
                    resolved = None

            if resolved and resolved.get("origin_iata") and resolved.get("dest_iata") and resolved.get("hotel_city_code"):
                try:
                    data = amadeus_search(
                        origin_iata=resolved["origin_iata"],
                        dest_iata=resolved["dest_iata"],
                        hotel_city_code=resolved["hotel_city_code"],
                        start_date=str(start_date),
                        nights=int(nights),
                        adults=int(adults),
                        children=int(children),
                    )
                    debug_tools["search"] = data.get("debug")
                    sr = data.get("search_results") or empty_search_results()
                    ctx["last_search_results"] = sr

                    plans = build_plan_choices_10(sr, nights=nights)
                    ctx["plan_choices"] = plans
                    ctx["current_plan"] = None

                    tool_data["search"] = sr
                    tool_data["plan_choices"] = plans
                except ResponseError as e:
                    debug_tools["search"] = {"amadeus_error": {"status": getattr(e, "status_code", None), "body": getattr(getattr(e, "response", None), "body", None)}}
                except Exception as e:
                    debug_tools["search"] = {"error": str(e)}

    # agent respond (final)
    respond_context = {
        "today": date.today().isoformat(),
        "slots": ctx.get("slots"),
        "resolved": tool_data["resolved"],
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": ctx.get("plan_choices") or [],
        "current_plan": ctx.get("current_plan"),
        "policy": {"never_ask_iata": True, "be_autonomous": True},
    }
    resp = agent_call(user_id, mode="respond", user_message=user_message, context=respond_context)

    response_text = resp.get("response") if isinstance(resp, dict) else None
    if not isinstance(response_text, str) or not response_text.strip():
        response_text = "รับทราบค่ะ ✅ ฉันอัปเดตผลการค้นหาให้แล้ว ลองเลือกช้อยส์ได้เลยค่ะ"

    out = {
        "response": response_text.strip(),
        "travel_slots": ctx.get("slots") or {},
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": ctx.get("plan_choices") or [],
        "current_plan": ctx.get("current_plan"),
        "suggestions": (resp.get("suggestions") if isinstance(resp, dict) and isinstance(resp.get("suggestions"), list) else ["เลือกช้อยส์ 1", "เลือกช้อยส์ 2", "ปรับจำนวนคืน"]),
        "debug": {"agent_decide": dec, "agent_respond": resp, "tools": debug_tools},
    }

    apply_memory_update(user_id, dec.get("memory_update") if isinstance(dec, dict) else None)
    apply_memory_update(user_id, resp.get("memory_update") if isinstance(resp, dict) else None)

    push_history(user_id, "user", user_message)
    push_history(user_id, "assistant", out["response"])

    USER_CONTEXTS[user_id] = ctx
    return out


# ============================================================
# 7) FastAPI
# ============================================================
app = FastAPI(title="AI Travel Agent – Gemini CLI 100% Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "demo_user"


@app.get("/health")
async def health():
    exe, exe_dbg = locate_gemini_cli()
    ok = bool(exe)
    ver = None
    err = None
    if exe:
        try:
            p = subprocess.run([exe, "--version"], text=True, capture_output=True, timeout=3, check=False)
            ver = (p.stdout or p.stderr or "").strip()
            if p.returncode != 0:
                ok = False
                err = (p.stderr or p.stdout or "").strip()[-800:]
        except Exception as e:
            ok = False
            err = str(e)

    return {
        "status": "ok",
        "amadeus_env": AMADEUS_ENV,
        "amadeus_host": AMADEUS_HOST,
        "gemini_cli": {"env": GEMINI_CLI_BIN_ENV, "resolved": exe, "ok": ok, "version": ver, "err": err, "debug": exe_dbg},
        "gemini_model": GEMINI_MODEL_NAME,
        "stateful": {"users_in_memory": len(USER_CONTEXTS)},
    }


@app.post("/api/gemini_ping")
async def gemini_ping():
    try:
        raw = gemini_cli('ตอบกลับเป็น JSON เท่านั้น: {"ok": true, "msg": "pong"}', model=GEMINI_MODEL_NAME, timeout_s=60)
        data = safe_extract_json(raw)
        return data if isinstance(data, dict) else {"ok": True, "msg": "pong", "raw": raw}
    except Exception as e:
        return {"ok": False, "error": str(e), "debug": where_gemini_debug()}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    user_id = (req.user_id or "demo_user").strip()
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is empty")

    try:
        return orchestrate_chat(user_id=user_id, user_message=msg)
    except GeminiCLLError as e:
        raise HTTPException(status_code=500, detail={"type": "GeminiCLLError", "message": str(e)})
    except ResponseError as e:
        raise HTTPException(
            status_code=int(getattr(e, "status_code", 500) or 500),
            detail={"type": "AmadeusResponseError", "body": getattr(getattr(e, "response", None), "body", None)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"type": "UnhandledException", "message": str(e), "traceback": traceback.format_exc()})
