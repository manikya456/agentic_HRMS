from django.db.models import Avg, Sum, Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrHR
from agentic.models import AgentRun, AgentPendingAction, AuditLog
from agentic.serializers import (
    AgentRunSerializer,
    AgentRunDetailSerializer,
    AgentPendingActionSerializer,
    AuditLogSerializer,
    RunAgentRequestSerializer,
    ActionDecisionSerializer,
)
from agentic.engine.orchestrator import AgentOrchestrator
from agentic.tools.registry import tool_registry


class AgentRunListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = AgentRunSerializer
    queryset = AgentRun.objects.all().order_by("-created_at")

    def create(self, request, *args, **kwargs):
        req_serializer = RunAgentRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        data = req_serializer.validated_data

        run = AgentOrchestrator.execute_workflow(
            trigger_type=data["trigger_type"],
            goal=data["goal"],
            params=data.get("parameters", {}),
            user=request.user,
        )

        detail_serializer = AgentRunDetailSerializer(run)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class AgentRunDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = AgentRunDetailSerializer
    lookup_field = "trace_id"
    queryset = AgentRun.objects.all()


class PendingActionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = AgentPendingActionSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status", "PENDING")
        qs = AgentPendingAction.objects.all().order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class PendingActionDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def post(self, request, action_id):
        action = AgentPendingAction.objects.filter(id=action_id).first()
        if not action:
            return Response({"detail": "Pending action not found."}, status=status.HTTP_404_NOT_FOUND)

        if action.status != AgentPendingAction.ActionStatus.PENDING:
            return Response(
                {"detail": f"Action has already been {action.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ActionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        feedback = serializer.validated_data.get("feedback", "")

        action.reviewed_by = request.user
        action.reviewed_at = timezone.now()

        execution_result = {}
        if decision == "APPROVE":
            action.status = AgentPendingAction.ActionStatus.APPROVED
            # Execute the staged action
            tool = tool_registry.get_tool(action.action_type)
            if tool:
                execution_result = tool.execute(**action.payload)
            else:
                execution_result = {"warning": f"Tool {action.action_type} executed as human confirmed."}

            AuditLog.objects.create(
                actor=request.user,
                action=f"APPROVED_{action.action_type}",
                entity_type="AgentPendingAction",
                entity_id=str(action.id),
                metadata={
                    "payload": action.payload,
                    "feedback": feedback,
                    "execution_result": execution_result,
                },
            )
        else:
            action.status = AgentPendingAction.ActionStatus.REJECTED
            AuditLog.objects.create(
                actor=request.user,
                action=f"REJECTED_{action.action_type}",
                entity_type="AgentPendingAction",
                entity_id=str(action.id),
                metadata={"payload": action.payload, "feedback": feedback},
            )

        action.save()

        # Update run status if all actions resolved
        if action.run:
            remaining = action.run.pending_actions.filter(status=AgentPendingAction.ActionStatus.PENDING).count()
            if remaining == 0:
                action.run.status = AgentRun.Status.COMPLETED
                action.run.save(update_fields=["status"])

        return Response(
            {
                "action": AgentPendingActionSerializer(action).data,
                "execution_result": execution_result,
            },
            status=status.HTTP_200_OK,
        )


class AuditLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().order_by("-timestamp")


class AgentMetricsSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        total_runs = AgentRun.objects.count()
        aggregates = AgentRun.objects.aggregate(
            avg_latency=Avg("latency_ms"),
            total_tokens=Sum("total_tokens"),
            avg_reflection=Avg("reflection_score"),
            total_cost=Sum("estimated_cost"),
        )
        total_actions = AgentPendingAction.objects.count()
        pending_actions = AgentPendingAction.objects.filter(status=AgentPendingAction.ActionStatus.PENDING).count()
        approved_actions = AgentPendingAction.objects.filter(status=AgentPendingAction.ActionStatus.APPROVED).count()

        approval_rate = (approved_actions / max(total_actions, 1)) * 100

        return Response({
            "total_runs": total_runs,
            "avg_latency_ms": round(aggregates.get("avg_latency") or 0, 1),
            "total_tokens_used": aggregates.get("total_tokens") or 0,
            "avg_reflection_score": round(aggregates.get("avg_reflection") or 100, 1),
            "total_estimated_cost_usd": round(float(aggregates.get("total_cost") or 0), 4),
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "approved_actions": approved_actions,
            "approval_rate": round(approval_rate, 1),
        })


class AvailableToolsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        return Response({"tools": tool_registry.list_tools()})
