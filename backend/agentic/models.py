import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class AgentRun(models.Model):
    class TriggerType(models.TextChoices):
        MANUAL = "MANUAL", "Manual Prompt"
        RECRUITMENT_PIPELINE = "RECRUITMENT_PIPELINE", "Autonomous Recruitment Pipeline"
        LEAVE_AUDIT = "LEAVE_AUDIT", "Autonomous Leave & Attendance Audit"
        CUSTOM_INSTRUCTION = "CUSTOM_INSTRUCTION", "Custom HR Copilot Instruction"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        AWAITING_APPROVAL = "AWAITING_APPROVAL", "Awaiting Human Approval"

    trace_id = models.CharField(max_length=64, unique=True, db_index=True, default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_runs")
    goal = models.CharField(max_length=500)
    trigger_type = models.CharField(max_length=40, choices=TriggerType.choices, default=TriggerType.MANUAL)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    total_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    reflection_score = models.PositiveIntegerField(default=100)
    plan = models.JSONField(default=list, blank=True)
    result_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AgentRun {self.trace_id[:8]} - {self.goal[:30]} ({self.status})"


class AgentStepLog(models.Model):
    class StepStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        RETRIED = "RETRIED", "Retried"
        SKIPPED = "SKIPPED", "Skipped"

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="step_logs")
    step_index = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    tool_name = models.CharField(max_length=120)
    tool_input = models.JSONField(default=dict, blank=True)
    tool_output = models.JSONField(default=dict, blank=True)
    reflection_critique = models.TextField(blank=True)
    reflection_score = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=StepStatus.choices, default=StepStatus.SUCCESS)
    latency_ms = models.PositiveIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["step_index"]

    def __str__(self):
        return f"Step {self.step_index}: {self.title} [{self.status}]"


class AgentPendingAction(models.Model):
    class ActionStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="pending_actions", null=True, blank=True)
    action_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=ActionStatus.choices, default=ActionStatus.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_agent_actions")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Action: {self.title} ({self.status})"


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_audit_logs")
    action = models.CharField(max_length=150)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.action} on {self.entity_type} {self.entity_id}"
