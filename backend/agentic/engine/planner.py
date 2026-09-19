from typing import Any, Dict, List, Optional
import json
import logging
from recruitment.models import Candidate, JobOpening
from core.models import LeaveRequest
from recruitment.services import _azure_openai_chat, _parse_json_response

logger = logging.getLogger("agentic.planner")


class AgentPlanner:
    """
    Decomposes automation goals or natural language HR requests into
    an ordered, executable workflow graph with conditional branching and HITL nodes.
    """

    @classmethod
    def create_plan(cls, trigger_type: str, goal: str, params: Optional[Dict[str, Any]] = None, user: Optional[Any] = None) -> List[Dict[str, Any]]:
        params = params or {}

        if trigger_type == "RECRUITMENT_PIPELINE":
            return cls._plan_recruitment_pipeline(params)
        elif trigger_type == "LEAVE_AUDIT":
            return cls._plan_leave_audit(params)
        else:
            return cls._plan_custom_instruction(goal, params, user)

    @classmethod
    def _plan_recruitment_pipeline(cls, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        job_id = params.get("job_opening_id")
        candidate_ids = params.get("candidate_ids")

        if not candidate_ids:
            # Query candidates
            query = Candidate.objects.all()
            if job_id:
                query = query.filter(applied_position_id=job_id)
            # Prioritize candidates without evaluations or up to 5 candidates for batch
            candidates = list(query.order_by("-created_at")[:5])
            candidate_ids = [c.id for c in candidates]

        steps = []
        for idx, cid in enumerate(candidate_ids):
            cand = Candidate.objects.filter(id=cid).first()
            name = cand.name if cand else f"Candidate #{cid}"
            job_name = cand.applied_position.title if cand and cand.applied_position else "Role"

            # Step 1: Resume Screening
            steps.append({
                "step_index": len(steps),
                "title": f"Screen Resume: {name} for {job_name}",
                "tool_name": "resume_screening",
                "arguments": {"candidate_id": cid, "job_opening_id": job_id},
                "requires_approval": False,
                "is_conditional": False,
            })

            # Step 2: Generate Interview Questions (runs dynamically / prepared)
            steps.append({
                "step_index": len(steps),
                "title": f"Plan Voice Interview Questions for {name}",
                "tool_name": "interview_planner",
                "arguments": {"candidate_id": cid, "count": 3},
                "requires_approval": False,
                "is_conditional": True,
                "condition": "match_score >= 50",
            })

            # Step 3: Human-in-the-Loop Node
            steps.append({
                "step_index": len(steps),
                "title": f"Human Approval: Candidate Status for {name}",
                "tool_name": "candidate_status_update",
                "arguments": {"candidate_id": cid, "new_status": "Shortlisted", "reason": "Recommended by Agentic Screening"},
                "requires_approval": True,
                "is_conditional": False,
            })

        return steps

    @classmethod
    def _plan_leave_audit(cls, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        leave_ids = params.get("leave_request_ids")
        if not leave_ids:
            pending_leaves = list(LeaveRequest.objects.filter(status=LeaveRequest.LeaveStatus.PENDING).order_by("-created_at")[:10])
            leave_ids = [l.id for l in pending_leaves]

        steps = []
        for lid in leave_ids:
            leave = LeaveRequest.objects.filter(id=lid).select_related("employee").first()
            emp_name = leave.employee.full_name if leave else f"Leave #{lid}"

            # Step 1: Leave Audit Tool
            steps.append({
                "step_index": len(steps),
                "title": f"Audit Leave Request for {emp_name}",
                "tool_name": "leave_audit",
                "arguments": {"leave_request_id": lid},
                "requires_approval": False,
                "is_conditional": False,
            })

            # Step 2: Human-in-the-Loop Decision Node
            steps.append({
                "step_index": len(steps),
                "title": f"Human Review Node: Sign-off for {emp_name}",
                "tool_name": "leave_status_update",
                "arguments": {"leave_request_id": lid, "new_status": "APPROVED", "comment": "Agentic Audit recommendation"},
                "requires_approval": True,
                "is_conditional": False,
            })

        return steps

    @classmethod
    def _plan_custom_instruction(cls, goal: str, params: Dict[str, Any], user: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Dynamically generates an execution plan from free-form natural language instructions.
        Uses LLM planning prompt with rule-based keyword fallback.
        """
        prompt = f"""
You are an expert HRMS Agent Planner. Decompose the user's HR goal into 2 to 4 executable steps.
Available tools:
- resume_screening (arguments: candidate_id, job_opening_id)
- interview_planner (arguments: candidate_id, count)
- leave_audit (arguments: leave_request_id)
- employee_data_retriever (arguments: user_id, query)
- notification_dispatcher (arguments: recipient_id, title, message)

Goal: {goal}

Return only valid JSON with this schema:
{{
  "steps": [
    {{
      "title": "Short title",
      "tool_name": "one of the available tools",
      "arguments": {{}},
      "requires_approval": false
    }}
  ]
}}
"""
        response = _azure_openai_chat(prompt)
        parsed = _parse_json_response(response) if response else None

        if parsed and isinstance(parsed, dict) and isinstance(parsed.get("steps"), list):
            steps = []
            for idx, item in enumerate(parsed["steps"]):
                steps.append({
                    "step_index": idx,
                    "title": str(item.get("title", f"Step {idx + 1}")),
                    "tool_name": str(item.get("tool_name", "employee_data_retriever")),
                    "arguments": item.get("arguments", {}),
                    "requires_approval": bool(item.get("requires_approval", False)),
                    "is_conditional": False,
                })
            if steps:
                return steps

        # Semantic Rule-based fallback planner
        goal_lower = goal.lower()
        user_id = getattr(user, "id", 1) if user else 1

        if any(term in goal_lower for term in ["leave", "absence", "time off", "vacation"]):
            return cls._plan_leave_audit(params)
        elif any(term in goal_lower for term in ["resume", "candidate", "screen", "hire", "recruit", "interview"]):
            return cls._plan_recruitment_pipeline(params)
        else:
            return [
                {
                    "step_index": 0,
                    "title": f"Query HR Knowledge Base: {goal[:40]}",
                    "tool_name": "employee_data_retriever",
                    "arguments": {"user_id": user_id, "query": goal},
                    "requires_approval": False,
                    "is_conditional": False,
                }
            ]
