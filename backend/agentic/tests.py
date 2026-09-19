from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Employee, Attendance, LeaveRequest
from recruitment.models import JobOpening, Candidate
from agentic.models import AgentRun, AgentPendingAction, AuditLog
from agentic.tools.registry import tool_registry
from agentic.engine.reflection import StepReflector
from agentic.engine.planner import AgentPlanner
from agentic.engine.orchestrator import AgentOrchestrator

User = get_user_model()


class AgenticSystemTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@test.com",
            username="admin@test.com",
            password="Password123!",
            role="ADMIN",
        )
        self.employee_user = User.objects.create_user(
            email="emp@test.com",
            username="emp@test.com",
            password="Password123!",
            role="EMPLOYEE",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            employee_id="EMP-101",
            full_name="Jane Doe",
            department="Engineering",
            designation="Backend Engineer",
            salary=90000,
            joining_date="2025-01-01",
        )
        self.job = JobOpening.objects.create(
            title="Senior Python Developer",
            department="Engineering",
            description="We need an experienced Python & Django engineer.",
            required_skills="Python, Django, PostgreSQL, Docker",
            experience_required="3+ years",
        )
        self.candidate = Candidate.objects.create(
            name="Alex Kumar",
            email="alex@example.com",
            applied_position=self.job,
        )

    def test_tool_registry_registration(self):
        tools = tool_registry.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("resume_screening", names)
        self.assertIn("interview_planner", names)
        self.assertIn("leave_audit", names)
        self.assertIn("employee_data_retriever", names)

    def test_reflection_clamps_and_detects_hallucinations(self):
        # Raw tool output with score > 100 and hallucinated matched skills
        raw_output = {
            "match_score": 115,
            "extracted_skills": ["Python", "Django"],
            "matched_skills": ["Python", "QuantumComputing", "Cybersecurity"],
            "status": "Review",
        }
        ref_score, critique, sanitized = StepReflector.reflect("resume_screening", {}, raw_output)
        self.assertEqual(sanitized["match_score"], 100)
        self.assertIn("Python", sanitized["matched_skills"])
        self.assertNotIn("QuantumComputing", sanitized["matched_skills"])
        self.assertIn("QuantumComputing", critique)

    def test_planner_creates_recruitment_workflow(self):
        plan = AgentPlanner.create_plan(
            trigger_type="RECRUITMENT_PIPELINE",
            goal="Screen candidate Alex",
            params={"candidate_ids": [self.candidate.id], "job_opening_id": self.job.id},
            user=self.user,
        )
        self.assertGreaterEqual(len(plan), 2)
        tool_names = [step["tool_name"] for step in plan]
        self.assertIn("resume_screening", tool_names)
        self.assertIn("interview_planner", tool_names)

    def test_orchestrator_runs_and_generates_traces(self):
        run = AgentOrchestrator.execute_workflow(
            trigger_type="RECRUITMENT_PIPELINE",
            goal="Automate screening for Alex Kumar",
            params={"candidate_ids": [self.candidate.id], "job_opening_id": self.job.id},
            user=self.user,
        )
        self.assertTrue(run.trace_id)
        self.assertGreater(run.step_logs.count(), 0)
        self.assertIn(run.status, [AgentRun.Status.COMPLETED, AgentRun.Status.AWAITING_APPROVAL])
        # Check audit log recorded
        audit = AuditLog.objects.filter(entity_id=run.trace_id).first()
        self.assertIsNotNone(audit)
