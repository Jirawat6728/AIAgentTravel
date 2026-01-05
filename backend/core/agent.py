from __future__ import annotations
from typing import Any, Dict, List
import random

# ===== Badges/Labels =====
LABELS = [
    ("ถูกสุด", "green"),
    ("เร็วสุด", "blue"),
    ("ประหยัด", "teal"),
    ("สมดุล", "purple"),
    ("สบาย", "orange"),
    ("พรีเมี่ยม", "gold"),
]

def pick_label(idx: int) -> tuple[str, str]:
    return LABELS[idx % len(LABELS)]

# ===== Plan Choices Builder =====

def _thb(amount: float) -> int:
    return int(round(amount))

def build_plan_choices(max_choices: int = 10) -> List[Dict[str, Any]]:
    base_price = random.randint(12000, 26000)
    choices: List[Dict[str, Any]] = []

    for i in range(max_choices):
        label, color = pick_label(i)
        multiplier = {
            "ถูกสุด": 0.85,
            "ประหยัด": 0.92,
            "สมดุล": 1.00,
            "เร็วสุด": 1.08,
            "สบาย": 1.15,
            "พรีเมี่ยม": 1.35,
        }[label]
        total = _thb(base_price * (1 + i * 0.03) * multiplier)

        flights = [{
            "from": "BKK",
            "to": "HKT",
            "airline": random.choice(["TG", "FD", "SL", "PG"]),
            "dep": "08:30",
            "arr": "10:00",
            "duration_min": random.choice([85, 90, 95]),
            "stops": 0,
            "price_thb": _thb(total * 0.62),
        }]
        hotels = [{
            "name": random.choice(["Patong Bay Hotel", "Sunset Stay", "Andaman Comfort", "Lagoon Resort"]),
            "area": random.choice(["Patong", "Kata", "Karon"]),
            "nights": 3,
            "stars": random.choice([5, 4]) if label in ("สบาย", "พรีเมี่ยม") else random.choice([3, 4]),
            "price_thb": _thb(total * 0.28),
        }]
        cars = [{
            "company": random.choice(["Avis", "Hertz", "Sixt", "LocalRent"]),
            "type": random.choice(["SUV", "Compact"]) if label in ("สบาย", "พรีเมี่ยม") else random.choice(["Eco", "Compact"]),
            "days": 3,
            "price_thb": _thb(total * 0.10),
        }]
        ferries = [{
            "route": "Rassada Pier → Phi Phi",
            "operator": random.choice(["Andaman Wave", "Sea Angel", "PhiPhi Cruiser"]),
            "time": random.choice(["09:00", "11:00", "13:30"]),
            "duration_min": random.choice([60, 75, 90]),
            "price_thb": random.randint(450, 950),
        }]

        choices.append({
            "id": i + 1,
            "label": label,
            "color": color,
            "total_price_thb": total,
            "components": {
                "flights": flights,
                "hotels": hotels,
                "cars": cars,
                "ferries": ferries,
            }
        })

    choices.sort(key=lambda x: x["total_price_thb"])
    for idx, c in enumerate(choices, start=1):
        c["id"] = idx
    return choices

def build_itinerary(choice: Dict[str, Any]) -> Dict[str, Any]:
    comps = choice["components"]
    return {
        "title": f"ทริปตัวเลือก {choice['id']} ({choice['label']})",
        "days": [
            {"day": 1, "items": [
                {"type": "flight", **comps["flights"][0]},
                {"type": "hotel_checkin", "hotel": comps["hotels"][0]["name"], "area": comps["hotels"][0]["area"]},
            ]},
            {"day": 2, "items": [
                {"type": "car", **comps["cars"][0]},
                {"type": "ferry", **comps["ferries"][0]},
            ]},
            {"day": 3, "items": [
                {"type": "free", "note": "พักผ่อน/เที่ยวตามสไตล์"},
            ]},
            {"day": 4, "items": [
                {"type": "checkout", "hotel": comps["hotels"][0]["name"]},
                {"type": "flight", **comps["flights"][0], "from": "HKT", "to": "BKK", "dep": "18:20", "arr": "19:50"},
            ]},
        ],
        "price": {"currency": "THB", "total": choice["total_price_thb"]},
    }
