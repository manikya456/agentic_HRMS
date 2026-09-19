from rest_framework import serializers
from agentic.models import AgentRun, AgentStepLog, AgentPendingAction, AuditLog


class AgentStepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentStepLog
        fields = [
            "id",
            "step_index",
            "title",
            "tool_name",
            "tool_input",
            "tool_output",
            "reflection_critique",
            "reflection_score",
            "status",
            "latency_ms",
            "tokens_used",
            "retry_count",
            "created_at",
        ]


class AgentPendingActionSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewed_by.get_full_name", read_only=True)

    class Meta:
        model = AgentPendingAction
        fields = [
            "id",
            "run",
            "action_type",
            "title",
            "description",
            "payload",
            "status",
            "reviewed_by",
            "reviewer_name",
            "reviewed_at",
            "created_at",
        ]


class AgentRunSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    steps_count = serializers.IntegerField(source="step_logs.count", read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "trace_id",
            "user",
            "user_name",
            "goal",
            "trigger_type",
            "status",
            "total_tokens",
            "latency_ms",
            "estimated_cost",
            "reflection_score",
            "plan",
            "result_summary",
            "steps_count",
            "created_at",
            "updated_at",
        ]


class AgentRunDetailSerializer(AgentRunSerializer):
    step_logs = AgentStepLogSerializer(many=True, read_only=True)
    pending_actions = AgentPendingActionSerializer(many=True, read_only=True)

    class Meta(AgentRunSerializer.Meta):
        fields = AgentRunSerializer.Meta.fields + ["step_logs", "pending_actions"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "entity_type",
            "entity_id",
            "metadata",
            "timestamp",
        ]


class RunAgentRequestSerializer(serializers.Serializer):
    trigger_type = serializers.ChoiceField(
        choices=AgentRun.TriggerType.choices,
        default=AgentRun.TriggerType.CUSTOM_INSTRUCTION,
    )
    goal = serializers.CharField(required=True, max_length=500)
    parameters = serializers.DictField(required=False, default=dict)


class ActionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"], default="APPROVE")
    feedback = serializers.CharField(required=False, allow_blank=True, default="")
