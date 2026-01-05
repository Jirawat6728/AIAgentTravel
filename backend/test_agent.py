"""
Test script for AI Travel Agent
Test the Agent system to verify it works correctly
"""

import asyncio
import sys
import os
# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

from core.orchestrator import orchestrate_chat
from core.context import get_user_ctx, update_user_ctx
from core.slots import DEFAULT_SLOTS

async def test_basic_search():
    """Test basic search functionality"""
    print("=" * 60)
    print("TEST 1: Basic Search")
    print("=" * 60)
    
    user_id = "test_user_001"
    user_message = "ฉันจะไปภูเก็ตจากกรุงเทพวันที่ 25 ธ.ค. 2568 ไป 3 คืน ไป 2 ผู้ใหญ่ 1 เด็ก"
    
    print(f"User message: {user_message}")
    print(f"User ID: {user_id}")
    print("\nProcessing...")
    
    try:
        result = await orchestrate_chat(
            user_id=user_id,
            user_message=user_message,
            existing_slots={},
            trip_id="test_trip_001",
            write_memory=False
        )
        
        print("\nResults:")
        print(f"  - Response: {result.get('response', 'N/A')[:200]}...")
        print(f"  - Plan choices: {len(result.get('plan_choices', []))} items")
        print(f"  - Agent state: {result.get('agent_state', {})}")
        print(f"  - Travel slots: {result.get('travel_slots', {})}")
        
        if result.get('plan_choices'):
            print("\n[PASS] System works correctly! Found plan choices")
        else:
            print("\n[WARN] No plan choices found (may be due to Amadeus Sandbox limitations)")
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_slot_extraction():
    """Test slot extraction"""
    print("\n" + "=" * 60)
    print("TEST 2: Slot Extraction")
    print("=" * 60)
    
    from services.gemini_service import slot_extract_with_gemini
    from datetime import date
    
    user_message = "ฉันจะไปนิวยอร์กจากเชียงใหม่วันที่ 3 ม.ค. 2569 ไป 7 วัน ไป 3 ผู้ใหญ่ 2 เด็ก ขอที่นั่ง Business class"
    today = date.today().isoformat()
    
    print(f"User message: {user_message}")
    print("\nExtracting slots...")
    
    try:
        slots, assumptions = slot_extract_with_gemini(today, "test_user", user_message, {})
        
        print("\nExtracted slots:")
        print(f"  - Origin: {slots.get('origin')}")
        print(f"  - Destination: {slots.get('destination')}")
        print(f"  - Start date: {slots.get('start_date')}")
        print(f"  - Nights: {slots.get('nights')}")
        print(f"  - Adults: {slots.get('adults')}")
        print(f"  - Children: {slots.get('children')}")
        print(f"  - Cabin class: {slots.get('cabin_class')}")
        print(f"  - Total travelers: {(slots.get('adults') or 0) + (slots.get('children') or 0)}")
        print(f"\nAssumptions: {assumptions}")
        
        # Check if traveler count is correct
        adults = slots.get('adults') or 0
        children = slots.get('children') or 0
        total = adults + children
        
        if adults == 3 and children == 2 and total == 5:
            print("\n[PASS] Traveler count is correct! (3 adults + 2 children = 5 people)")
        else:
            print(f"\n[WARN] Traveler count may be wrong: adults={adults}, children={children}, total={total}")
        
        return slots
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_planner_executor_narrator():
    """Test Planner-Executor-Narrator workflow"""
    print("\n" + "=" * 60)
    print("TEST 3: Planner-Executor-Narrator Workflow")
    print("=" * 60)
    
    from core.planner import Planner
    from core.executor import Executor
    from core.narrator import Narrator
    
    user_message = "ฉันจะไปโตเกียวจากกรุงเทพวันที่ 1 ม.ค. 2569 ไป 5 คืน ไป 2 ผู้ใหญ่"
    travel_slots = {
        "origin": "กรุงเทพ",
        "destination": "โตเกียว",
        "start_date": "2569-01-01",
        "nights": 5,
        "adults": 2,
        "children": 0
    }
    
    context = {
        "travel_slots": travel_slots,
        "last_travel_slots": travel_slots,
        "iata_cache": {}
    }
    
    print(f"User message: {user_message}")
    print(f"Travel slots: {travel_slots}")
    print("\nTesting PEN workflow...")
    
    try:
        # 1. Planner
        print("\n1. Planner: Analyzing...")
        planner = Planner()
        planner_output = await planner.plan(user_message, travel_slots, context)
        print(f"   [OK] Intent: {planner_output.intent}")
        print(f"   [OK] Should proceed: {planner_output.should_proceed}")
        print(f"   [OK] Goals: {planner_output.goals}")
        
        if not planner_output.should_proceed:
            print("   [WARN] Planner does not recommend proceeding")
            return
        
        # 2. Executor
        print("\n2. Executor: Searching...")
        executor = Executor()
        executor_output = await executor.execute(planner_output, travel_slots, context)
        print(f"   [OK] Success: {executor_output.success}")
        print(f"   [OK] Plan choices: {len(executor_output.plan_choices)} items")
        print(f"   [OK] Errors: {executor_output.errors}")
        
        # 3. Narrator
        print("\n3. Narrator: Generating response...")
        narrator_output = await Narrator.narrate(planner_output, executor_output, context)
        print(f"   [OK] Message: {narrator_output.message[:200]}...")
        print(f"   [OK] Reasoning: {narrator_output.reasoning}")
        print(f"   [OK] Next actions: {narrator_output.next_actions}")
        
        print("\n[PASS] PEN Workflow works correctly!")
        
        return {
            "planner": planner_output,
            "executor": executor_output,
            "narrator": narrator_output
        }
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 60)
    print("TEST 4: Error Handling")
    print("=" * 60)
    
    user_id = "test_user_002"
    user_message = "ฉันจะไปนิวยอร์กจากเชียงใหม่วันที่ 3 ม.ค. 2569 ไป 7 วัน ไป 3 ผู้ใหญ่ 2 เด็ก ขอที่นั่ง Business class"
    
    print(f"User message: {user_message}")
    print("   (Route that may not have data in Amadeus Sandbox)")
    print("\nTesting...")
    
    try:
        result = await orchestrate_chat(
            user_id=user_id,
            user_message=user_message,
            existing_slots={},
            trip_id="test_trip_002",
            write_memory=False
        )
        
        print("\nResults:")
        print(f"  - Response: {result.get('response', 'N/A')[:300]}...")
        print(f"  - Plan choices: {len(result.get('plan_choices', []))} items")
        print(f"  - Agent state: {result.get('agent_state', {})}")
        
        # Check if error message shows correct traveler count
        response = result.get('response', '')
        if '3 ผู้ใหญ่ 2 เด็ก' in response or '5 ท่าน' in response or 'รวม 5' in response:
            print("\n[PASS] Error message shows correct traveler count!")
        elif '4 ท่าน' in response or '4 คน' in response:
            print("\n[WARN] Error message may still show wrong count (4 people)")
        else:
            print("\n[INFO] No traveler count check found in response")
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AI Travel Agent System Test")
    print("=" * 60)
    print("\nTests to run:")
    print("  1. Basic Search")
    print("  2. Slot Extraction")
    print("  3. Planner-Executor-Narrator Workflow")
    print("  4. Error Handling")
    print("\n" + "=" * 60)
    
    results = {}
    
    # Test 1: Basic search
    results['basic_search'] = await test_basic_search()
    
    # Test 2: Slot extraction
    results['slot_extraction'] = await test_slot_extraction()
    
    # Test 3: PEN workflow
    results['pen_workflow'] = await test_planner_executor_narrator()
    
    # Test 4: Error handling
    results['error_handling'] = await test_error_handling()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = 0
    total = 4
    
    if results['basic_search']:
        print("[PASS] Test 1: Basic Search")
        passed += 1
    else:
        print("[FAIL] Test 1: Basic Search")
    
    if results['slot_extraction']:
        print("[PASS] Test 2: Slot Extraction")
        passed += 1
    else:
        print("[FAIL] Test 2: Slot Extraction")
    
    if results['pen_workflow']:
        print("[PASS] Test 3: PEN Workflow")
        passed += 1
    else:
        print("[FAIL] Test 3: PEN Workflow")
    
    if results['error_handling']:
        print("[PASS] Test 4: Error Handling")
        passed += 1
    else:
        print("[FAIL] Test 4: Error Handling")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())

