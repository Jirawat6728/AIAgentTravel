"""
Test script for Non-linear Conversation (การเปลี่ยนใจ)
ทดสอบว่าระบบรองรับการเปลี่ยนใจได้หรือไม่
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import orchestrate_chat
from core.slots import DEFAULT_SLOTS, normalize_non_core_defaults


async def test_correction_flow():
    """
    Test Scenario: การเปลี่ยนใจ
    Turn 1: User says "จองตั๋วไป เชียงใหม่ พรุ่งนี้"
    Turn 2: User changes mind "เอ้ย ไม่เอาเชียงใหม่แล้ว ไป ภูเก็ต ดีกว่า"
    Expected: System should update destination to Phuket, but keep the date
    """
    user_id = "test_user_correction"
    trip_id = "test_trip_1"
    
    print("=" * 60)
    print("Test: Non-linear Conversation (การเปลี่ยนใจ)")
    print("=" * 60)
    
    # Turn 1: Initial request
    print("\nTurn 1: User says 'จองตั๋วไป เชียงใหม่ พรุ่งนี้'")
    print("-" * 60)
    
    result1 = await orchestrate_chat(
        user_id=user_id,
        user_message="จองตั๋วไป เชียงใหม่ พรุ่งนี้",
        existing_slots=normalize_non_core_defaults(DEFAULT_SLOTS),
        trip_id=trip_id,
        write_memory=True,
    )
    
    print(f"Response: {result1.get('response', '')[:200]}...")
    print(f"Destination: {result1.get('travel_slots', {}).get('destination')}")
    print(f"Start Date: {result1.get('travel_slots', {}).get('start_date')}")
    print(f"Origin: {result1.get('travel_slots', {}).get('origin')}")
    
    # Get updated slots from result
    updated_slots = result1.get('travel_slots', {})
    
    # Turn 2: Change mind
    print("\nTurn 2: User changes mind 'เอ้ย ไม่เอาเชียงใหม่แล้ว ไป ภูเก็ต ดีกว่า'")
    print("-" * 60)
    
    result2 = await orchestrate_chat(
        user_id=user_id,
        user_message="เอ้ย ไม่เอาเชียงใหม่แล้ว ไป ภูเก็ต ดีกว่า",
        existing_slots=updated_slots,
        trip_id=trip_id,
        write_memory=True,
    )
    
    print(f"Response: {result2.get('response', '')[:200]}...")
    print(f"Destination: {result2.get('travel_slots', {}).get('destination')}")
    print(f"Start Date: {result2.get('travel_slots', {}).get('start_date')}")
    print(f"Origin: {result2.get('travel_slots', {}).get('origin')}")
    
    # Verify results
    print("\nVerification:")
    print("-" * 60)
    
    final_dest = result2.get('travel_slots', {}).get('destination', '').lower()
    final_date = result2.get('travel_slots', {}).get('start_date')
    
    # Check if destination changed to Phuket
    if 'phuket' in final_dest or 'ภูเก็ต' in final_dest or 'hkt' in final_dest.lower():
        print("[PASS] Destination changed to Phuket")
    else:
        print(f"[FAIL] Destination is '{final_dest}' (expected Phuket)")
    
    # Check if date is preserved
    if final_date:
        print(f"[PASS] Date preserved: {final_date}")
    else:
        print("[FAIL] Date was lost")
    
    # Check if response mentions the change
    response_text = result2.get('response', '').lower()
    if 'เปลี่ยน' in response_text or 'change' in response_text or 'ภูเก็ต' in response_text:
        print("[PASS] Response mentions the change")
    else:
        print("[WARN] Response might not mention the change")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


async def test_multiple_corrections():
    """
    Test Scenario: Multiple corrections
    Turn 1: "ไปญี่ปุ่น 25 ธ.ค."
    Turn 2: "เปลี่ยนใจไปเกาหลีแทน"
    Turn 3: "เอา เปลี่ยนเป็น 3 ผู้ใหญ่"
    Expected: Each correction should update only the mentioned field
    """
    user_id = "test_user_multiple"
    trip_id = "test_trip_2"
    
    print("\n" + "=" * 60)
    print("Test: Multiple Corrections")
    print("=" * 60)
    
    slots = normalize_non_core_defaults(DEFAULT_SLOTS)
    
    # Turn 1
    print("\nTurn 1: 'ไปญี่ปุ่น 25 ธ.ค.'")
    result1 = await orchestrate_chat(
        user_id=user_id,
        user_message="ไปญี่ปุ่น 25 ธ.ค.",
        existing_slots=slots,
        trip_id=trip_id,
        write_memory=True,
    )
    slots = result1.get('travel_slots', slots)
    print(f"Destination: {slots.get('destination')}, Date: {slots.get('start_date')}, Adults: {slots.get('adults')}")
    
    # Turn 2
    print("\nTurn 2: 'เปลี่ยนใจไปเกาหลีแทน'")
    result2 = await orchestrate_chat(
        user_id=user_id,
        user_message="เปลี่ยนใจไปเกาหลีแทน",
        existing_slots=slots,
        trip_id=trip_id,
        write_memory=True,
    )
    slots = result2.get('travel_slots', slots)
    print(f"Destination: {slots.get('destination')}, Date: {slots.get('start_date')}, Adults: {slots.get('adults')}")
    
    # Turn 3
    print("\nTurn 3: 'เอา เปลี่ยนเป็น 3 ผู้ใหญ่'")
    result3 = await orchestrate_chat(
        user_id=user_id,
        user_message="เอา เปลี่ยนเป็น 3 ผู้ใหญ่",
        existing_slots=slots,
        trip_id=trip_id,
        write_memory=True,
    )
    slots = result3.get('travel_slots', slots)
    print(f"Destination: {slots.get('destination')}, Date: {slots.get('start_date')}, Adults: {slots.get('adults')}")
    
    # Verify
    print("\nVerification:")
    print("-" * 60)
    final_dest = slots.get('destination', '').lower()
    final_date = slots.get('start_date')
    final_adults = slots.get('adults')
    
    if 'korea' in final_dest or 'เกาหลี' in final_dest:
        print("[PASS] Destination is Korea")
    else:
        print(f"[FAIL] Destination is '{final_dest}' (expected Korea)")
    
    if final_date:
        print(f"[PASS] Date preserved: {final_date}")
    else:
        print("[FAIL] Date was lost")
    
    if final_adults == 3:
        print("[PASS] Adults changed to 3")
    else:
        print(f"[FAIL] Adults is {final_adults} (expected 3)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    # Fix encoding for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\nStarting Correction Flow Tests...\n")
    
    # Test 1: Basic correction
    asyncio.run(test_correction_flow())
    
    # Test 2: Multiple corrections
    asyncio.run(test_multiple_corrections())
    
    print("\nAll tests completed!\n")

