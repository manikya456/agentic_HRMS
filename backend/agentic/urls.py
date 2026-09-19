from django.urls import path
from agentic.views import (
    AgentRunListCreateView,
    AgentRunDetailView,
    PendingActionListView,
    PendingActionDecisionView,
    AuditLogListView,
    AgentMetricsSummaryView,
    AvailableToolsView,
)

urlpatterns = [
    path("runs/", AgentRunListCreateView.as_view(), name="agent-runs-list-create"),
    path("runs/<str:trace_id>/", AgentRunDetailView.as_view(), name="agent-run-detail"),
    path("pending-actions/", PendingActionListView.as_view(), name="agent-pending-actions"),
    path("pending-actions/<int:action_id>/decision/", PendingActionDecisionView.as_view(), name="agent-action-decision"),
    path("audit-logs/", AuditLogListView.as_view(), name="agent-audit-logs"),
    path("metrics/", AgentMetricsSummaryView.as_view(), name="agent-metrics"),
    path("tools/", AvailableToolsView.as_view(), name="agent-tools"),
]
