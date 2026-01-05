"""
Executor Module - Level 3 Feature
Executes tools and assembles results
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ExecutorOutput:
    """
    Output from Executor: tool execution results
    """
    success: bool
    search_results: Dict[str, Any]
    plan_choices: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]  # What tools were called
    errors: List[str]  # Any errors encountered


class Executor:
    """
    Executor: Execute tools and assemble results
    Calls Amadeus, Google Maps, etc. and builds plan choices
    """
    
    def __init__(self):
        # Tool registry
        self.tools = {}
    
    async def execute(
        self,
        planner_output: Any,  # PlannerOutput
        travel_slots: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ExecutorOutput:
        """
        Execute tools based on planner output
        Calls tools according to planner's intent and constraints
        Returns structured results
        """
        # Import here to avoid circular dependency
        from services.amadeus_service import amadeus_search_async, amadeus_search_section_async, empty_search_results
        from core.plan_builder import build_plan_choices_3
        import asyncio
        
        tool_calls = []
        errors = []
        search_results = empty_search_results()
        plan_choices = []
        
        try:
            # Determine which tools to call based on planner intent
            intent = planner_output.intent
            constraints = planner_output.constraints
            
            if intent in ["search", "edit"]:
                # Call Amadeus search based on constraints
                tool_calls.append({"tool": "amadeus_search", "status": "calling", "constraints": constraints})
                
                # Execute search using existing search logic
                # This integrates with orchestrator's search mechanism
                search_results = await Executor._execute_amadeus_search(constraints, travel_slots, context)
                
                tool_calls.append({
                    "tool": "amadeus_search",
                    "status": "success" if search_results else "no_results",
                    "results_count": {
                        "flights": len((search_results.get("flights") or {}).get("data") or []),
                        "hotels": len((search_results.get("hotels") or {}).get("data") or [])
                    }
                })
                
                # After search, build plan choices
                if search_results:
                    tool_calls.append({"tool": "build_plan_choices", "status": "calling"})
                    try:
                        debug_info = context.get("debug", {})
                        plan_choices = await asyncio.wait_for(
                            build_plan_choices_3(search_results, travel_slots, debug_info),
                            timeout=12.0
                        )
                        tool_calls.append({
                            "tool": "build_plan_choices",
                            "status": "success",
                            "choices_count": len(plan_choices)
                        })
                    except asyncio.TimeoutError:
                        errors.append("Plan building timeout")
                        tool_calls.append({"tool": "build_plan_choices", "status": "timeout"})
            
            return ExecutorOutput(
                success=len(errors) == 0,
                search_results=search_results,
                plan_choices=plan_choices,
                tool_calls=tool_calls,
                errors=errors
            )
            
        except Exception as e:
            errors.append(str(e))
            return ExecutorOutput(
                success=False,
                search_results=empty_search_results(),
                plan_choices=[],
                tool_calls=tool_calls,
                errors=errors
            )
    
    @staticmethod
    async def _execute_amadeus_search(
        constraints: Dict[str, Any],
        travel_slots: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute Amadeus search based on constraints
        Integrates with existing search logic from orchestrator
        """
        from services.amadeus_service import amadeus_search_async, empty_search_results
        from core.slots import normalize_non_core_defaults
        
        # Merge constraints with travel_slots
        merged_slots = dict(travel_slots)
        merged_slots.update({k: v for k, v in constraints.items() if v is not None})
        merged_slots = normalize_non_core_defaults(merged_slots)
        
        # Execute search
        try:
            search_results = await amadeus_search_async(merged_slots)
            return search_results
        except Exception as e:
            import logging
            logging.error(f"Amadeus search failed: {e}")
            return empty_search_results()

