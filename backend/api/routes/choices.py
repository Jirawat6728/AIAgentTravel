from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.state import get_state
from core.agent import build_itinerary

router = APIRouter(prefix="/choices", tags=["choices"])

class SelectChoiceRequest(BaseModel):
    choice_id: int

@router.post("/select")
def select_choice(req: SelectChoiceRequest):
    st = get_state()
    if not st.last_plan_choices:
        raise HTTPException(status_code=400, detail="No plan choices available. Send a chat message first.")

    choice = next((c for c in st.last_plan_choices if c["id"] == req.choice_id), None)
    if not choice:
        raise HTTPException(status_code=404, detail="Choice not found")

    st.selected_choice_id = req.choice_id
    itinerary = build_itinerary(choice)

    return {
        "ok": True,
        "selected_choice": choice,
        "itinerary": itinerary,
        "next_steps": [
            {"id": "edit", "label": "ปรับทริป"},
            {"id": "continue", "label": "ไปขั้นตอนกรอกผู้เดินทาง"},
            {"id": "sandbox_booking", "label": "จองใน Sandbox (ทดสอบ)"},
        ],
    }
