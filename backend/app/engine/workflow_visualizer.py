"""
Production-Grade Workflow Visualizer
Creates ASCII diagrams and summaries for debugging and monitoring
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models.trip_plan import TripPlan, SegmentStatus
from app.engine.workflow_manager import WorkflowManager, WorkflowState, SlotState, WorkflowStage
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowVisualizer:
    """
    Production-grade workflow visualizer
    
    Features:
    - ASCII diagram of current workflow state
    - Slot status visualization
    - Progress tracking
    - Issue detection
    - Export to JSON for debugging
    """
    
    def __init__(self, workflow_manager: Optional[WorkflowManager] = None):
        """Initialize visualizer"""
        self.workflow_manager = workflow_manager or WorkflowManager()
        logger.info("WorkflowVisualizer initialized")
    
    def visualize(self, trip_plan: TripPlan, include_details: bool = True) -> str:
        """
        Create ASCII visualization of workflow
        
        Args:
            trip_plan: TripPlan object
            include_details: Include detailed slot information
            
        Returns:
            ASCII diagram as string
        """
        # Analyze workflow
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        
        # Build diagram
        lines = []
        lines.append("=" * 80)
        lines.append("🔄 WORKFLOW VISUALIZATION")
        lines.append("=" * 80)
        lines.append("")
        
        # Current stage
        lines.append(f"📍 Current Stage: {workflow_state.stage.value.upper()}")
        lines.append(f"📊 Progress: {workflow_state.progress_percentage:.1f}%")
        lines.append("")
        
        # Stage progression diagram
        lines.append("🗺️  Stage Progression:")
        lines.append(self._create_stage_diagram(workflow_state.stage))
        lines.append("")
        
        # Slot status
        if include_details:
            lines.append("🎯 Slot Status:")
            lines.append(self._create_slot_status_table(workflow_state.slots))
            lines.append("")
        
        # Next action
        if workflow_state.next_action:
            lines.append(f"⚡ Next Action: {workflow_state.next_action}")
        else:
            lines.append("✅ No pending actions")
        lines.append("")
        
        # Blocking issues
        if workflow_state.blocking_issues:
            lines.append("⚠️  Blocking Issues:")
            for issue in workflow_state.blocking_issues:
                lines.append(f"   • {issue}")
            lines.append("")
        
        # Summary
        lines.append("📋 Summary:")
        lines.append(f"   Total Slots: {len(workflow_state.slots)}")
        lines.append(f"   Completed: {sum(1 for s in workflow_state.slots if s.is_complete)}")
        lines.append(f"   In Progress: {sum(1 for s in workflow_state.slots if not s.is_complete)}")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _create_stage_diagram(self, current_stage: WorkflowStage) -> str:
        """Create ASCII diagram of stage progression"""
        stages = [
            WorkflowStage.INITIAL,
            WorkflowStage.PLANNING,
            WorkflowStage.SEARCHING,
            WorkflowStage.SELECTING,
            WorkflowStage.CONFIRMING,
            WorkflowStage.BOOKING,
            WorkflowStage.COMPLETE
        ]
        
        lines = []
        for i, stage in enumerate(stages):
            # Check if this is current stage
            is_current = (stage == current_stage)
            is_before = (stages.index(stage) < stages.index(current_stage))
            
            # Choose symbol
            if is_current:
                symbol = "🔵"  # Current
                marker = " <-- YOU ARE HERE"
            elif is_before:
                symbol = "✅"  # Completed
                marker = ""
            else:
                symbol = "⚪"  # Pending
                marker = ""
            
            # Format stage name
            stage_name = stage.value.upper().ljust(15)
            
            # Add line
            if i > 0:
                lines.append("   │")
            lines.append(f"   {symbol} {stage_name}{marker}")
        
        return "\n".join(lines)
    
    def _create_slot_status_table(self, slots: List[SlotState]) -> str:
        """Create ASCII table of slot statuses"""
        if not slots:
            return "   (No slots)"
        
        lines = []
        lines.append("   ┌─────────────────────┬────────┬───────────────┬─────────┬───────────┬──────────┐")
        lines.append("   │ Slot                │ Index  │ Status        │ Req     │ Options   │ Selected │")
        lines.append("   ├─────────────────────┼────────┼───────────────┼─────────┼───────────┼──────────┤")
        
        for slot in slots:
            slot_name = slot.slot_type.value[:19].ljust(19)
            index = str(slot.segment_index).ljust(6)
            status = slot.status.value[:13].ljust(13)
            has_req = "✓" if slot.has_requirements else "✗"
            has_opt = "✓" if slot.has_options else "✗"
            has_sel = "✓" if slot.has_selection else "✗"
            
            # Color status
            if slot.is_complete:
                status_marker = "✅"
            elif slot.is_ready_for_selection:
                status_marker = "🔵"
            elif slot.is_ready_for_search:
                status_marker = "🔍"
            else:
                status_marker = "⚪"
            
            lines.append(
                f"   │ {slot_name} │ {index} │ {status_marker} {status} │ {has_req.center(7)} │ {has_opt.center(9)} │ {has_sel.center(8)} │"
            )
        
        lines.append("   └─────────────────────┴────────┴───────────────┴─────────┴───────────┴──────────┘")
        
        return "\n".join(lines)
    
    def get_compact_status(self, trip_plan: TripPlan) -> str:
        """
        Get compact one-line status
        
        Example: "SEARCHING (60%) | 3/5 slots ready"
        """
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        
        stage = workflow_state.stage.value.upper()
        progress = workflow_state.progress_percentage
        completed = sum(1 for s in workflow_state.slots if s.is_complete)
        total = len(workflow_state.slots)
        
        return f"{stage} ({progress:.0f}%) | {completed}/{total} slots ready"
    
    def export_to_dict(self, trip_plan: TripPlan) -> Dict[str, Any]:
        """Export workflow state to dictionary for JSON/API"""
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        
        return {
            "stage": workflow_state.stage.value,
            "progress_percentage": round(workflow_state.progress_percentage, 2),
            "next_action": workflow_state.next_action,
            "blocking_issues": workflow_state.blocking_issues,
            "slots": [
                {
                    "slot_type": slot.slot_type.value,
                    "segment_index": slot.segment_index,
                    "status": slot.status.value,
                    "has_requirements": slot.has_requirements,
                    "has_options": slot.has_options,
                    "has_selection": slot.has_selection,
                    "is_ready_for_search": slot.is_ready_for_search,
                    "is_ready_for_selection": slot.is_ready_for_selection,
                    "is_complete": slot.is_complete
                }
                for slot in workflow_state.slots
            ],
            "summary": {
                "total_slots": len(workflow_state.slots),
                "completed_slots": sum(1 for s in workflow_state.slots if s.is_complete),
                "pending_slots": sum(1 for s in workflow_state.slots if not s.is_complete)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def create_progress_bar(self, trip_plan: TripPlan, width: int = 40) -> str:
        """
        Create ASCII progress bar
        
        Example: [████████████░░░░░░░░░] 60%
        """
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        progress = workflow_state.progress_percentage
        
        filled = int((progress / 100) * width)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        
        return f"[{bar}] {progress:.0f}%"
    
    def get_slot_summary(self, trip_plan: TripPlan) -> Dict[str, int]:
        """Get summary counts of slot statuses"""
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        
        summary = {
            "total": len(workflow_state.slots),
            "pending": 0,
            "searching": 0,
            "selecting": 0,
            "confirmed": 0,
            "complete": 0
        }
        
        for slot in workflow_state.slots:
            if slot.is_complete:
                summary["complete"] += 1
            elif slot.status == SegmentStatus.CONFIRMED:
                summary["confirmed"] += 1
            elif slot.status == SegmentStatus.SELECTING:
                summary["selecting"] += 1
            elif slot.status == SegmentStatus.SEARCHING:
                summary["searching"] += 1
            else:
                summary["pending"] += 1
        
        return summary
    
    def log_workflow_state(self, trip_plan: TripPlan, session_id: str):
        """Log workflow state to logger"""
        compact_status = self.get_compact_status(trip_plan)
        
        logger.info(
            f"[WORKFLOW] {compact_status}",
            extra={
                "session_id": session_id,
                "workflow_state": self.export_to_dict(trip_plan)
            }
        )
    
    def create_detailed_report(self, trip_plan: TripPlan) -> str:
        """Create detailed text report for debugging"""
        workflow_state = self.workflow_manager.analyze_workflow(trip_plan)
        
        lines = []
        lines.append("=" * 100)
        lines.append("📊 DETAILED WORKFLOW REPORT")
        lines.append("=" * 100)
        lines.append(f"Generated at: {datetime.utcnow().isoformat()}")
        lines.append("")
        
        # Workflow state
        lines.append("🔄 Workflow State:")
        lines.append(f"   Stage: {workflow_state.stage.value}")
        lines.append(f"   Progress: {workflow_state.progress_percentage:.2f}%")
        lines.append(f"   Next Action: {workflow_state.next_action or 'None'}")
        lines.append("")
        
        # Slots detail
        lines.append("🎯 Slot Details:")
        for slot in workflow_state.slots:
            lines.append(f"   • {slot.slot_type.value}[{slot.segment_index}]:")
            lines.append(f"     - Status: {slot.status.value}")
            lines.append(f"     - Requirements: {'✓' if slot.has_requirements else '✗'}")
            lines.append(f"     - Options: {'✓' if slot.has_options else '✗'}")
            lines.append(f"     - Selection: {'✓' if slot.has_selection else '✗'}")
            lines.append(f"     - Ready for search: {'✓' if slot.is_ready_for_search else '✗'}")
            lines.append(f"     - Ready for selection: {'✓' if slot.is_ready_for_selection else '✗'}")
            lines.append(f"     - Complete: {'✓' if slot.is_complete else '✗'}")
        lines.append("")
        
        # Issues
        if workflow_state.blocking_issues:
            lines.append("⚠️  Issues:")
            for issue in workflow_state.blocking_issues:
                lines.append(f"   • {issue}")
        else:
            lines.append("✅ No blocking issues")
        lines.append("")
        
        # Route map
        lines.append("🗺️  Available Actions by Stage:")
        route_map = self.workflow_manager.get_route_map()
        for stage, actions in route_map.items():
            actions_str = ", ".join(actions) if actions else "None"
            lines.append(f"   {stage}: {actions_str}")
        lines.append("")
        
        lines.append("=" * 100)
        
        return "\n".join(lines)


# Global visualizer instance
workflow_visualizer = WorkflowVisualizer()
