import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import api from "@/lib/api";
import {
  Bot,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  Zap,
  Sparkles,
  Layers,
  ArrowRight,
  UserCheck,
  UserX,
  RefreshCw,
  Coins,
  History,
  FileCheck2,
  CalendarCheck,
  Search,
} from "lucide-react";

interface AgentStepLog {
  id: number;
  step_index: number;
  title: string;
  tool_name: string;
  tool_input: any;
  tool_output: any;
  reflection_critique: string;
  reflection_score: number;
  status: string;
  latency_ms: number;
  tokens_used: number;
  retry_count: number;
  created_at: string;
}

interface AgentPendingAction {
  id: number;
  run: number;
  action_type: string;
  title: string;
  description: string;
  payload: any;
  status: "PENDING" | "APPROVED" | "REJECTED";
  reviewer_name?: string;
  created_at: string;
}

interface AgentRun {
  id: number;
  trace_id: string;
  goal: string;
  trigger_type: string;
  status: string;
  total_tokens: number;
  latency_ms: number;
  estimated_cost: string;
  reflection_score: number;
  plan: any[];
  result_summary: string;
  created_at: string;
  step_logs?: AgentStepLog[];
  pending_actions?: AgentPendingAction[];
}

interface AgentMetrics {
  total_runs: number;
  avg_latency_ms: number;
  total_tokens_used: number;
  avg_reflection_score: number;
  total_estimated_cost_usd: number;
  total_actions: number;
  pending_actions: number;
  approved_actions: number;
  approval_rate: number;
}

interface AuditLog {
  id: number;
  actor_name?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: any;
  timestamp: string;
}

export default function AgenticHubPage() {
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [activeRun, setActiveRun] = useState<AgentRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([]);
  const [pendingActions, setPendingActions] = useState<AgentPendingAction[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [activeTab, setActiveTab] = useState<"launch" | "trace" | "approvals" | "history">("launch");
  const [customGoal, setCustomGoal] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const fetchMetrics = () => {
    api.get("/agentic/metrics/").then((res) => setMetrics(res.data)).catch(() => {});
    api.get("/agentic/pending-actions/?status=PENDING").then((res) => setPendingActions(res.data.results || res.data)).catch(() => {});
    api.get("/agentic/runs/").then((res) => setRecentRuns(res.data.results || res.data)).catch(() => {});
    api.get("/agentic/audit-logs/").then((res) => setAuditLogs(res.data.results || res.data)).catch(() => {});
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const triggerWorkflow = async (triggerType: string, defaultGoal: string, parameters = {}) => {
    setIsRunning(true);
    setActionFeedback(null);
    try {
      const response = await api.post("/agentic/run/", {
        trigger_type: triggerType,
        goal: defaultGoal,
        parameters,
      });
      setActiveRun(response.data);
      setSelectedTraceId(response.data.trace_id);
      setActiveTab("trace");
      fetchMetrics();
    } catch (err: any) {
      alert("Failed to execute agent workflow: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsRunning(false);
    }
  };

  const loadTrace = async (traceId: string) => {
    try {
      const response = await api.get(`/agentic/runs/${traceId}/`);
      setActiveRun(response.data);
      setSelectedTraceId(traceId);
      setActiveTab("trace");
    } catch (err) {
      console.error(err);
    }
  };

  const handleDecision = async (actionId: number, decision: "APPROVE" | "REJECT") => {
    try {
      const response = await api.post(`/agentic/pending-actions/${actionId}/decision/`, {
        decision,
        feedback: `Reviewed by HR Console (${decision})`,
      });
      setActionFeedback(`Action ${decision === "APPROVE" ? "Approved & Executed" : "Rejected"} successfully!`);
      fetchMetrics();
      if (selectedTraceId) {
        loadTrace(selectedTraceId);
      }
    } catch (err: any) {
      alert("Decision failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200/80 dark:border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-500 flex items-center justify-center text-white shadow-glow">
              <Bot className="h-5 w-5" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              Agentic AI Automation Hub
            </h1>
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Autonomous multi-step HR orchestration with dynamic planning, tool abstractions, grounded reflection, and human-in-the-loop safeguards.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 py-1.5 px-3">
            <ShieldCheck className="h-3.5 w-3.5 mr-1.5 inline" /> Grounded Reflection Active
          </Badge>
          <Badge className="bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20 py-1.5 px-3">
            <Zap className="h-3.5 w-3.5 mr-1.5 inline" /> 7 Tools Registered
          </Badge>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-5 border border-slate-200/60 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Agent Runs</p>
            <Bot className="h-4 w-4 text-sky-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">
            {metrics?.total_runs ?? 0}
          </p>
          <span className="text-xs text-slate-500 mt-1 block">Autonomous workflows completed</span>
        </Card>

        <Card className="p-5 border border-slate-200/60 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Avg Reflection Score</p>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-emerald-600 dark:text-emerald-400">
            {metrics?.avg_reflection_score ?? 100}%
          </p>
          <span className="text-xs text-slate-500 mt-1 block">Factually grounded & anti-hallucination</span>
        </Card>

        <Card className="p-5 border border-slate-200/60 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Avg Step Latency</p>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">
            {metrics?.avg_latency_ms ? `${metrics.avg_latency_ms} ms` : "0 ms"}
          </p>
          <span className="text-xs text-slate-500 mt-1 block">Bounded retry resilience</span>
        </Card>

        <Card className="p-5 border border-slate-200/60 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Token Cost (USD)</p>
            <Coins className="h-4 w-4 text-purple-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">
            ${metrics?.total_estimated_cost_usd?.toFixed(4) ?? "0.0000"}
          </p>
          <span className="text-xs text-slate-500 mt-1 block">{metrics?.total_tokens_used ?? 0} tokens tracked</span>
        </Card>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab("launch")}
          className={`pb-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === "launch"
              ? "border-sky-500 text-sky-600 dark:text-sky-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Play className="h-4 w-4" /> Launch Automation
        </button>

        <button
          onClick={() => setActiveTab("trace")}
          className={`pb-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === "trace"
              ? "border-sky-500 text-sky-600 dark:text-sky-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Layers className="h-4 w-4" /> Live Execution Trace {activeRun && `(${activeRun.trace_id.slice(0, 8)})`}
        </button>

        <button
          onClick={() => setActiveTab("approvals")}
          className={`pb-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === "approvals"
              ? "border-sky-500 text-sky-600 dark:text-sky-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <UserCheck className="h-4 w-4" /> Human-in-the-Loop Node
          {pendingActions.length > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs font-bold rounded-full bg-amber-500 text-white">
              {pendingActions.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`pb-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === "history"
              ? "border-sky-500 text-sky-600 dark:text-sky-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <History className="h-4 w-4" /> Audit Trail & History
        </button>
      </div>

      {/* TAB 1: LAUNCH AUTOMATIONS */}
      {activeTab === "launch" && (
        <div className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Automation 1: Autonomous Recruitment Pipeline */}
            <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl flex flex-col justify-between hover:shadow-lg transition">
              <div>
                <div className="h-12 w-12 rounded-2xl bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center mb-4">
                  <FileCheck2 className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                  Autonomous Recruitment Pipeline
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                  Decomposes candidate intake into an end-to-end agent workflow:
                </p>
                <ul className="mt-3 space-y-2 text-xs text-slate-500 dark:text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                    Tool 1: Resume text extraction & skill matching against JD
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                    Reflection: Anti-hallucination check on matched skills & score bounds
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                    Tool 2: Custom interview question set generation based on gap areas
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                    HITL Node: Queues shortlisting decision for HR approval
                  </li>
                </ul>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80">
                <Button
                  onClick={() => triggerWorkflow("RECRUITMENT_PIPELINE", "Autonomous Screening and Interview Prep")}
                  disabled={isRunning}
                  className="w-full bg-sky-600 hover:bg-sky-500 text-white rounded-xl py-2.5 font-medium flex items-center justify-center gap-2 shadow-glow"
                >
                  {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Launch Recruitment Agent
                </Button>
              </div>
            </Card>

            {/* Automation 2: Leave & Attendance Audit */}
            <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl flex flex-col justify-between hover:shadow-lg transition">
              <div>
                <div className="h-12 w-12 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4">
                  <CalendarCheck className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                  Autonomous Leave & Attendance Auditor
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                  Systematic policy and attendance cross-verification:
                </p>
                <ul className="mt-3 space-y-2 text-xs text-slate-500 dark:text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    Queries all pending employee leave requests
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    Analyzes historical 30-day attendance & punctuality ratio
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    Evaluates team concurrency (detects capacity bottlenecks)
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    HITL Node: Stages evidence-backed recommendations for HR approval
                  </li>
                </ul>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80">
                <Button
                  onClick={() => triggerWorkflow("LEAVE_AUDIT", "Audit All Pending Leaves and Attendance Patterns")}
                  disabled={isRunning}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl py-2.5 font-medium flex items-center justify-center gap-2 shadow-glow"
                >
                  {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Launch Leave Auditor Agent
                </Button>
              </div>
            </Card>
          </div>

          {/* Natural Language Instruction Copilot */}
          <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-2">
              <Sparkles className="h-5 w-5" />
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Natural Language HR Operations Copilot
              </h3>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              Enter any high-level administrative command. The dynamic planner will decompose the instruction into an executable tool graph.
            </p>

            <div className="flex gap-3">
              <Input
                value={customGoal}
                onChange={(e) => setCustomGoal(e.target.value)}
                placeholder="e.g., Audit pending leaves this week and explain any risky absences..."
                className="flex-1 rounded-xl bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800"
              />
              <Button
                onClick={() => {
                  if (!customGoal.trim()) return;
                  triggerWorkflow("CUSTOM_INSTRUCTION", customGoal);
                }}
                disabled={isRunning || !customGoal.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl px-6"
              >
                {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : "Devise & Execute Plan"}
              </Button>
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              <span className="font-semibold text-slate-700 dark:text-slate-300">Sample instructions:</span>
              <button
                type="button"
                onClick={() => setCustomGoal("Audit all pending leaves and identify low attendance staff")}
                className="hover:underline text-sky-600 dark:text-sky-400 cursor-pointer"
              >
                "Audit all pending leaves"
              </button>
              •
              <button
                type="button"
                onClick={() => setCustomGoal("Screen candidates and prepare voice interview questions")}
                className="hover:underline text-sky-600 dark:text-sky-400 cursor-pointer"
              >
                "Screen candidates & prep interview"
              </button>
              •
              <button
                type="button"
                onClick={() => setCustomGoal("Query company department headcount and open positions")}
                className="hover:underline text-sky-600 dark:text-sky-400 cursor-pointer"
              >
                "Query headcount & open positions"
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: LIVE EXECUTION TRACE */}
      {activeTab === "trace" && (
        <div className="space-y-6">
          {!activeRun ? (
            <Card className="p-12 text-center border-dashed border-2 border-slate-200 dark:border-slate-800 bg-transparent">
              <Bot className="h-10 w-10 text-slate-400 mx-auto mb-3" />
              <p className="text-slate-600 dark:text-slate-400 font-medium">No active execution trace selected.</p>
              <p className="text-xs text-slate-500 mt-1">
                Launch an automated workflow from the "Launch Automation" tab, or pick a trace from History.
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* Run Overview Banner */}
              <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        Trace: {activeRun.trace_id}
                      </span>
                      <Badge
                        className={
                          activeRun.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                            : activeRun.status === "AWAITING_APPROVAL"
                            ? "bg-amber-500/10 text-amber-600 border-amber-500/20"
                            : "bg-sky-500/10 text-sky-600 border-sky-500/20"
                        }
                      >
                        {activeRun.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <h2 className="text-xl font-bold mt-2 text-slate-900 dark:text-white">
                      {activeRun.goal}
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                      {activeRun.result_summary || "Workflow executed successfully."}
                    </p>
                  </div>

                  <div className="flex gap-4 text-xs font-medium">
                    <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 block">Total Latency</span>
                      <span className="text-base font-bold text-slate-900 dark:text-white">{activeRun.latency_ms} ms</span>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 block">Total Tokens</span>
                      <span className="text-base font-bold text-slate-900 dark:text-white">{activeRun.total_tokens}</span>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 block">Est. Cost</span>
                      <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">${Number(activeRun.estimated_cost).toFixed(5)}</span>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 block">Reflection Score</span>
                      <span className="text-base font-bold text-sky-600 dark:text-sky-400">{activeRun.reflection_score}%</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Step By Step Execution Cards */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                  <Layers className="h-4 w-4 text-sky-500" /> Executed Workflow Steps ({activeRun.step_logs?.length ?? 0})
                </h3>

                {activeRun.step_logs?.map((step) => (
                  <Card
                    key={step.id}
                    className="p-5 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl transition hover:border-slate-300 dark:hover:border-slate-700"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/60 pb-3">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center justify-center h-7 w-7 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 font-bold text-xs">
                          {step.step_index + 1}
                        </span>
                        <div>
                          <h4 className="font-semibold text-slate-900 dark:text-white text-base">
                            {step.title}
                          </h4>
                          <span className="text-xs font-mono text-slate-500">
                            Tool: {step.tool_name}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs">
                        <Badge className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {step.latency_ms} ms
                        </Badge>
                        <Badge className="bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20">
                          {step.tokens_used} tokens
                        </Badge>
                        <Badge
                          className={
                            step.status === "SUCCESS"
                              ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                          }
                        >
                          {step.status}
                        </Badge>
                      </div>
                    </div>

                    {/* Step Output & Reflection Critique */}
                    <div className="mt-4 grid md:grid-cols-2 gap-4 text-xs">
                      {/* Tool Output Data */}
                      <div className="bg-slate-50 dark:bg-slate-900/80 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
                        <p className="font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" /> Tool Result Payload:
                        </p>
                        <pre className="text-[11px] overflow-x-auto text-slate-600 dark:text-slate-400 font-mono whitespace-pre-wrap max-h-48">
                          {JSON.stringify(step.tool_output, null, 2)}
                        </pre>
                      </div>

                      {/* Reflection & Grounding Critique */}
                      <div className="bg-emerald-50/50 dark:bg-emerald-950/20 rounded-xl p-3 border border-emerald-100 dark:border-emerald-900/30">
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-semibold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> Grounded Reflection:
                          </p>
                          <span className="font-bold text-emerald-700 dark:text-emerald-400 text-xs">
                            Score: {step.reflection_score}%
                          </span>
                        </div>
                        <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-xs">
                          {step.reflection_critique || "Output inspected and confirmed within valid ranges."}
                        </p>
                        {step.retry_count > 0 && (
                          <p className="mt-2 text-amber-600 dark:text-amber-400 text-[11px] flex items-center gap-1">
                            <RefreshCw className="h-3 w-3" /> Recovered via bounded retry (attempt {step.retry_count + 1})
                          </p>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: HUMAN-IN-THE-LOOP ACTIONS */}
      {activeTab === "approvals" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Human-in-the-Loop Safeguard Queue
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Sensitive decisions staged by the agent requiring human authorization before taking effect.
              </p>
            </div>
            {actionFeedback && (
              <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 py-1 px-3">
                {actionFeedback}
              </Badge>
            )}
          </div>

          {pendingActions.length === 0 ? (
            <Card className="p-12 text-center border-dashed border-2 border-slate-200 dark:border-slate-800 bg-transparent">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto mb-3" />
              <p className="text-slate-700 dark:text-slate-300 font-semibold">No pending actions awaiting approval.</p>
              <p className="text-xs text-slate-500 mt-1">All proposed actions have been reviewed or none are currently queued.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {pendingActions.map((action) => (
                <Card
                  key={action.id}
                  className="p-5 border border-amber-200/80 dark:border-amber-900/40 bg-amber-50/20 dark:bg-amber-950/10 rounded-2xl"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-amber-500/10 text-amber-600 border-amber-500/20">
                          {action.action_type}
                        </Badge>
                        <span className="text-xs text-slate-500">
                          {new Date(action.created_at).toLocaleString()}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                        {action.title}
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                        {action.description}
                      </p>
                      <div className="mt-2 bg-white/80 dark:bg-slate-900/80 p-2.5 rounded-lg text-xs font-mono border border-slate-100 dark:border-slate-800 max-w-xl overflow-x-auto">
                        {JSON.stringify(action.payload, null, 2)}
                      </div>
                    </div>

                    <div className="flex gap-2 shrink-0">
                      <Button
                        onClick={() => handleDecision(action.id, "APPROVE")}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs px-4 py-2 font-medium flex items-center gap-1.5"
                      >
                        <UserCheck className="h-4 w-4" /> Approve & Execute
                      </Button>
                      <Button
                        onClick={() => handleDecision(action.id, "REJECT")}
                        variant="ghost"
                        className="border border-red-200 text-red-600 hover:bg-red-50 dark:border-red-900 dark:text-red-400 rounded-xl text-xs px-4 py-2 font-medium flex items-center gap-1.5"
                      >
                        <UserX className="h-4 w-4" /> Reject
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: AUDIT TRAIL & HISTORY */}
      {activeTab === "history" && (
        <div className="space-y-6">
          <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <History className="h-5 w-5 text-sky-500" /> Recent Agent Executions
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="pb-3 px-3">Trace ID</th>
                    <th className="pb-3 px-3">Goal / Workflow</th>
                    <th className="pb-3 px-3">Status</th>
                    <th className="pb-3 px-3">Latency</th>
                    <th className="pb-3 px-3">Tokens</th>
                    <th className="pb-3 px-3">Cost</th>
                    <th className="pb-3 px-3">Date</th>
                    <th className="pb-3 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {recentRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition">
                      <td className="py-3 px-3 font-mono text-sky-600 dark:text-sky-400">
                        {run.trace_id.slice(0, 8)}...
                      </td>
                      <td className="py-3 px-3 font-medium text-slate-800 dark:text-slate-200 max-w-xs truncate">
                        {run.goal}
                      </td>
                      <td className="py-3 px-3">
                        <Badge
                          className={
                            run.status === "COMPLETED"
                              ? "bg-emerald-500/10 text-emerald-600"
                              : run.status === "AWAITING_APPROVAL"
                              ? "bg-amber-500/10 text-amber-600"
                              : "bg-slate-100 text-slate-700"
                          }
                        >
                          {run.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-400">{run.latency_ms} ms</td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-400">{run.total_tokens}</td>
                      <td className="py-3 px-3 text-emerald-600 font-mono">${Number(run.estimated_cost).toFixed(4)}</td>
                      <td className="py-3 px-3 text-slate-500">{new Date(run.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-3 text-right">
                        <Button
                          onClick={() => loadTrace(run.trace_id)}
                          variant="ghost"
                          className="text-xs text-sky-600 hover:text-sky-500 py-1 px-2.5 h-auto"
                        >
                          View Trace <ArrowRight className="h-3 w-3 ml-1" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* System Audit Log Section */}
          <Card className="p-6 border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-500" /> Immutable System Audit Log
            </h3>
            <div className="space-y-2">
              {auditLogs.slice(0, 10).map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{log.action}</span>
                    <span className="text-slate-500">
                      on {log.entity_type} {log.entity_id ? `(${log.entity_id.slice(0, 8)})` : ""}
                    </span>
                    {log.actor_name && (
                      <span className="text-sky-600 dark:text-sky-400">by {log.actor_name}</span>
                    )}
                  </div>
                  <span className="text-slate-400">{new Date(log.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
