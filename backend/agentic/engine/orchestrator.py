import time
import uuid
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from agentic.models import AgentRun, AgentStepLog, AgentPendingAction, AuditLog
from agentic.tools.registry import tool_registry
from .planner import AgentPlanner
from .reflection import StepReflector
from .retry import bounded_retry

logger = logging.getLogger("agentic.orchestrator")


class AgentOrchestrator:
    """
    Central execution engine that orchestrates:
    Planner -> Tool Invocations -> Bounded Retries -> Reflection -> HITL nodes -> Tracing.
    """

    @classmethod
    def execute_workflow(
        cls,
        trigger_type: str,
        goal: str,
        params: Optional[Dict[str, Any]] = None,
        user: Optional[Any] = None,
    ) -> AgentRun:
        trace_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        run = AgentRun.objects.create(
            trace_id=trace_id,
            user=user,
            goal=goal,
            trigger_type=trigger_type,
            status=AgentRun.Status.RUNNING,
        )

        try:
            # 1. Dynamic Planning
            plan = AgentPlanner.create_plan(trigger_type, goal, params, user)
            run.plan = plan
            run.save(update_fields=["plan"])

            total_tokens = 0
            reflection_scores = []
            pending_actions_created = 0

            # 2. Sequential Step Execution with Reflection & Tracing
            last_step_data = {}
            for step in plan:
                step_index = step.get("step_index", 0)
                step_title = step.get("title", f"Step {step_index + 1}")
                tool_name = step.get("tool_name")
                args = dict(step.get("arguments", {}))
                requires_approval = step.get("requires_approval", False)

                # Check condition if present
                if step.get("is_conditional"):
                    match_score = last_step_data.get("match_score", 0)
                    if match_score < 50:
                        AgentStepLog.objects.create(
                            run=run,
                            step_index=step_index,
                            title=f"[Skipped] {step_title}",
                            tool_name=tool_name,
                            tool_input=args,
                            tool_output={"skipped_reason": f"Condition not met: match_score={match_score} < 50"},
                            reflection_critique="Step bypassed conditionally based on candidate scoring threshold.",
                            status=AgentStepLog.StepStatus.SKIPPED,
                        )
                        continue

                # Human-in-the-loop Node
                if requires_approval:
                    action_desc = f"Approval required for: {step_title}"
                    pending = AgentPendingAction.objects.create(
                        run=run,
                        action_type=tool_name,
                        title=step_title,
                        description=action_desc,
                        payload=args,
                        status=AgentPendingAction.ActionStatus.PENDING,
                    )
                    pending_actions_created += 1

                    AgentStepLog.objects.create(
                        run=run,
                        step_index=step_index,
                        title=f"[Human Node] {step_title}",
                        tool_name=tool_name,
                        tool_input=args,
                        tool_output={"action_id": pending.id, "status": "QUEUED_FOR_APPROVAL"},
                        reflection_critique="Sensitive operational action safely delegated to Human-in-the-Loop approval queue.",
                        reflection_score=100,
                        status=AgentStepLog.StepStatus.SUCCESS,
                    )
                    continue

                # Autonomous Tool Execution
                tool = tool_registry.get_tool(tool_name)
                step_start = time.perf_counter()
                retry_count = 0

                if not tool:
                    AgentStepLog.objects.create(
                        run=run,
                        step_index=step_index,
                        title=step_title,
                        tool_name=tool_name,
                        tool_input=args,
                        tool_output={"error": f"Tool '{tool_name}' not found in registry."},
                        status=AgentStepLog.StepStatus.FAILED,
                    )
                    continue

                def call_tool():
                    return tool.execute(**args)

                tool_res, retries, _ = bounded_retry(call_tool, max_retries=3)
                step_duration_ms = int((time.perf_counter() - step_start) * 1000)
                raw_data = tool_res.get("data", {})

                # Reflection & Self-Correction Step
                ref_score, critique, sanitized_data = StepReflector.reflect(tool_name, args, raw_data)
                reflection_scores.append(ref_score)
                last_step_data = sanitized_data

                # Token estimation
                step_tokens = max(120, len(str(args)) // 4 + len(str(sanitized_data)) // 4)
                total_tokens += step_tokens

                AgentStepLog.objects.create(
                    run=run,
                    step_index=step_index,
                    title=step_title,
                    tool_name=tool_name,
                    tool_input=args,
                    tool_output=sanitized_data,
                    reflection_critique=critique,
                    reflection_score=ref_score,
                    status=AgentStepLog.StepStatus.SUCCESS if tool_res.get("success") else AgentStepLog.StepStatus.FAILED,
                    latency_ms=step_duration_ms,
                    tokens_used=step_tokens,
                    retry_count=retries,
                )

            total_duration_ms = int((time.perf_counter() - start_time) * 1000)
            avg_reflection = int(sum(reflection_scores) / max(len(reflection_scores), 1))
            # Standard gpt-4o / mini blended cost estimation: ~$0.000003 per token
            est_cost = Decimal(str(round(total_tokens * 0.000003, 6)))

            run.latency_ms = total_duration_ms
            run.total_tokens = total_tokens
            run.estimated_cost = est_cost
            run.reflection_score = avg_reflection
            run.status = (
                AgentRun.Status.AWAITING_APPROVAL
                if pending_actions_created > 0
                else AgentRun.Status.COMPLETED
            )
            run.result_summary = (
                f"Completed {len(plan)} planned steps in {total_duration_ms}ms. "
                f"Average reflection score: {avg_reflection}%. "
                f"{pending_actions_created} action(s) staged for Human Review."
            )
            run.save()

            # Record audit log
            AuditLog.objects.create(
                actor=user,
                action=f"AGENT_RUN_{trigger_type}",
                entity_type="AgentRun",
                entity_id=run.trace_id,
                metadata={
                    "steps_count": len(plan),
                    "pending_actions": pending_actions_created,
                    "tokens": total_tokens,
                    "latency_ms": total_duration_ms,
                },
            )

            return run

        except Exception as exc:
            logger.exception(f"Error during agent run {trace_id}: {exc}")
            run.status = AgentRun.Status.FAILED
            run.result_summary = f"Execution failed: {str(exc)}"
            run.latency_ms = int((time.perf_counter() - start_time) * 1000)
            run.save()
            return run
