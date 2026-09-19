from typing import Any, Dict, List, Optional
from core.models import Attendance, Employee, LeaveRequest, Notification
from recruitment.models import Candidate, JobOpening, ResumeEvaluation, InterviewSession
from recruitment.services import (
    evaluate_candidate_resume,
    generate_role_questions,
)
from core.hr_chat import answer_hr_question
from .base import BaseAgentTool


class ResumeScreeningTool(BaseAgentTool):
    name = "resume_screening"
    description = (
        "Screens a candidate resume against a job opening. Extracts candidate skills, "
        "compares with job requirements, and computes match score, matched skills, and recommendations."
    )
    parameters_schema = {
        "candidate_id": {"type": "integer", "required": True, "description": "ID of candidate to screen"},
        "job_opening_id": {"type": "integer", "required": False, "description": "Optional specific job opening ID"},
    }
    requires_human_approval = False

    def run(self, candidate_id: int, job_opening_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found.")

        if job_opening_id:
            job = JobOpening.objects.filter(id=job_opening_id).first()
            if job:
                candidate.applied_position = job
                candidate.save(update_fields=["applied_position"])

        score, extracted, matched, missing, recommendation, analysis, status = evaluate_candidate_resume(candidate)

        # Update or create ResumeEvaluation
        eval_obj, _ = ResumeEvaluation.objects.update_or_create(
            candidate=candidate,
            defaults={
                "skill_match_percentage": score,
                "extracted_skills": extracted,
                "matched_skills": matched,
                "missing_skills": missing,
                "recommendation": recommendation,
                "status": status,
                "ai_summary": analysis,
            },
        )

        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "job_title": candidate.applied_position.title if candidate.applied_position else "General",
            "match_score": score,
            "extracted_skills": extracted,
            "matched_skills": matched,
            "missing_skills": missing,
            "recommendation": recommendation,
            "status": status,
            "analysis": analysis,
        }


class InterviewPlannerTool(BaseAgentTool):
    name = "interview_planner"
    description = (
        "Generates customized, role-tailored voice interview questions for a candidate based on job requirements "
        "and identified skill gaps from resume screening."
    )
    parameters_schema = {
        "candidate_id": {"type": "integer", "required": True, "description": "Candidate ID"},
        "count": {"type": "integer", "required": False, "description": "Number of questions to generate (default 3)"},
    }
    requires_human_approval = False

    def run(self, candidate_id: int, count: int = 3, **kwargs) -> Dict[str, Any]:
        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found.")

        position = candidate.applied_position
        role_name = position.title if position else "General Software Engineer"
        questions = generate_role_questions(role_name, job_opening=position, candidate=candidate, count=count)

        # Prepare or update an InterviewSession
        session, created = InterviewSession.objects.get_or_create(
            candidate=candidate,
            defaults={
                "role": role_name,
                "questions": questions,
                "current_question_index": 0,
            },
        )
        if not created and (not session.questions or len(session.questions) < count):
            session.questions = questions
            session.role = role_name
            session.save(update_fields=["questions", "role"])

        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "role": role_name,
            "questions_count": len(questions),
            "generated_questions": questions,
            "session_id": session.id,
        }


class LeaveAuditTool(BaseAgentTool):
    name = "leave_audit"
    description = (
        "Audits pending employee leave requests against attendance history, attendance ratio, "
        "and department workload to produce intelligent approval/rejection recommendations."
    )
    parameters_schema = {
        "leave_request_id": {"type": "integer", "required": True, "description": "ID of LeaveRequest to audit"},
    }
    requires_human_approval = False

    def run(self, leave_request_id: int, **kwargs) -> Dict[str, Any]:
        leave = LeaveRequest.objects.filter(id=leave_request_id).select_related("employee").first()
        if not leave:
            raise ValueError(f"Leave request with ID {leave_request_id} not found.")

        employee = leave.employee
        recent_records = list(Attendance.objects.filter(employee=employee).order_by("-date")[:20])

        total_days = len(recent_records)
        present_count = sum(1 for r in recent_records if r.status == "PRESENT")
        absent_count = sum(1 for r in recent_records if r.status == "ABSENT")
        attendance_ratio = (present_count / max(total_days, 1)) * 100

        # Concurrent leaves in same department
        concurrent_leaves = LeaveRequest.objects.filter(
            employee__department=employee.department,
            status=LeaveRequest.LeaveStatus.APPROVED,
            start_date__lte=leave.end_date,
            end_date__gte=leave.start_date,
        ).exclude(id=leave.id).count()

        # Decision rule
        if attendance_ratio < 60:
            recommendation = "Reject Leave"
            reason = f"Employee attendance ratio over past {total_days} days is {attendance_ratio:.1f}% (below 60% threshold)."
        elif concurrent_leaves >= 2:
            recommendation = "Review Further"
            reason = f"High departmental concurrency: {concurrent_leaves} colleagues in {employee.department} are already on leave during this period."
        else:
            recommendation = "Approve Leave"
            reason = f"Healthy attendance ({attendance_ratio:.1f}%) and normal department coverage."

        leave.ai_suggestion = recommendation
        leave.save(update_fields=["ai_suggestion"])

        return {
            "leave_request_id": leave.id,
            "employee_id": employee.employee_id,
            "employee_name": employee.full_name,
            "department": employee.department,
            "leave_type": leave.leave_type,
            "duration": f"{leave.start_date} to {leave.end_date}",
            "attendance_ratio": round(attendance_ratio, 1),
            "department_concurrent_leaves": concurrent_leaves,
            "recommendation": recommendation,
            "reason": reason,
        }


class EmployeeDataTool(BaseAgentTool):
    name = "employee_data_retriever"
    description = "Retrieves employee profile, attendance, leave, or departmental operational records via semantic search and database."
    parameters_schema = {
        "user_id": {"type": "integer", "required": True, "description": "Requesting User ID"},
        "query": {"type": "string", "required": True, "description": "Natural language query regarding HR data"},
    }
    requires_human_approval = False

    def run(self, user_id: int, query: str, **kwargs) -> Dict[str, Any]:
        from accounts.models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found.")

        result = answer_hr_question(user, query)
        return {
            "query": query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }


class CandidateStatusUpdateTool(BaseAgentTool):
    name = "candidate_status_update"
    description = "Updates a candidate's recruitment status (e.g. Shortlisted, Review, Rejected). Requires human review."
    parameters_schema = {
        "candidate_id": {"type": "integer", "required": True},
        "new_status": {"type": "string", "required": True, "enum": ["Shortlisted", "Review", "Rejected"]},
        "reason": {"type": "string", "required": True},
    }
    requires_human_approval = True

    def run(self, candidate_id: int, new_status: str, reason: str, **kwargs) -> Dict[str, Any]:
        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found.")

        eval_obj = getattr(candidate, "evaluation", None)
        if eval_obj:
            eval_obj.status = new_status
            eval_obj.save(update_fields=["status"])

        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "new_status": new_status,
            "reason": reason,
            "applied": True,
        }


class LeaveStatusUpdateTool(BaseAgentTool):
    name = "leave_status_update"
    description = "Updates leave request status to Approved or Rejected. Requires human review."
    parameters_schema = {
        "leave_request_id": {"type": "integer", "required": True},
        "new_status": {"type": "string", "required": True, "enum": ["APPROVED", "REJECTED"]},
        "comment": {"type": "string", "required": False},
    }
    requires_human_approval = True

    def run(self, leave_request_id: int, new_status: str, comment: str = "", **kwargs) -> Dict[str, Any]:
        leave = LeaveRequest.objects.filter(id=leave_request_id).first()
        if not leave:
            raise ValueError(f"Leave request {leave_request_id} not found.")

        leave.status = new_status
        leave.save(update_fields=["status"])

        return {
            "leave_request_id": leave.id,
            "employee_id": leave.employee.employee_id,
            "new_status": new_status,
            "comment": comment,
            "applied": True,
        }


class NotificationDispatchTool(BaseAgentTool):
    name = "notification_dispatcher"
    description = "Dispatches in-app notifications to employees, HR personnel, or candidates."
    parameters_schema = {
        "recipient_id": {"type": "integer", "required": True},
        "title": {"type": "string", "required": True},
        "message": {"type": "string", "required": True},
    }
    requires_human_approval = False

    def run(self, recipient_id: int, title: str, message: str, **kwargs) -> Dict[str, Any]:
        from accounts.models import User
        recipient = User.objects.filter(id=recipient_id).first()
        if not recipient:
            raise ValueError(f"Recipient user {recipient_id} not found.")

        notif = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
        )
        return {
            "notification_id": notif.id,
            "recipient_email": recipient.email,
            "title": title,
            "dispatched": True,
        }


class ToolRegistry:
    """Central registry holding all available tools."""
    def __init__(self):
        self._tools: Dict[str, BaseAgentTool] = {}
        self.register(ResumeScreeningTool())
        self.register(InterviewPlannerTool())
        self.register(LeaveAuditTool())
        self.register(EmployeeDataTool())
        self.register(CandidateStatusUpdateTool())
        self.register(LeaveStatusUpdateTool())
        self.register(NotificationDispatchTool())

    def register(self, tool: BaseAgentTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseAgentTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]


tool_registry = ToolRegistry()
