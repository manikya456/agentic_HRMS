# 💼 AI-HRMS: Intelligent Human Resource Management System with Agentic AI

> **A modern, full-stack Human Resource Management System (HRMS) powered by autonomous Agentic AI workflows to streamline recruitment, interview preparation, leave auditing, and daily workforce operations.**

---

## 📑 Table of Contents

1. [Project Overview & Problem Statement](#-project-overview--problem-statement)
2. [What is Agentic AI in this System?](#-what-is-agentic-ai-in-this-system)
3. [System Architecture](#-system-architecture)
4. [The 3 Autonomous Workflow Agents](#-the-3-autonomous-workflow-agents)
5. [The 7 Functional Tool Agents](#-the-7-functional-tool-agents)
6. [Grounded Reflection & Anti-Hallucination Engine](#-grounded-reflection--anti-hallucination-engine)
7. [Core Operational HR Modules](#-core-operational-hr-modules)
8. [Role-Based Access Control (RBAC) Matrix](#-role-based-access-control-rbac-matrix)
9. [Tech Stack & Dependencies](#-tech-stack--dependencies)
10. [Step-by-Step Installation & Setup Guide](#-step-by-step-installation--setup-guide)
11. [REST API Endpoint Reference](#-rest-api-endpoint-reference)
12. [Testing & Quality Assurance](#-testing--quality-assurance)
13. [Security, Privacy & Responsible AI](#-security-privacy--responsible-ai)

---

## 📌 Project Overview & Problem Statement

### The Problem
Traditional Human Resource Management Systems (HRMS) act as passive databases. HR personnel and managers spend hundreds of hours every month on tedious, manual, and disconnected tasks:
- **Resume Screening**: Manually downloading and reading dozens of PDF resumes to match technical skills against job descriptions.
- **Interview Preparation**: Writing customized questions from scratch for each applicant's background and skill gaps.
- **Leave Requests & Bottlenecks**: Manually cross-referencing attendance spreadsheets and checking if multiple team members requested leave on the same days.
- **Data Fragmentation**: Juggling disparate tools for payroll calculations, attendance check-ins, performance reviews, and employee queries.

### The Solution: AI-HRMS
**AI-HRMS** solves these operational pain points by integrating **standard enterprise HR operations** with an **autonomous Agentic AI orchestration layer**. 

Rather than simply providing a basic chatbot, AI-HRMS deploys **goal-oriented AI agents** that dynamically formulate plans, use specialized tools, cross-examine their own outputs to eliminate hallucinations, and safely stage high-impact actions for human manager approval.

---

## 🤖 What is Agentic AI in this System?

### Traditional AI vs. Agentic AI

| Capability | Traditional AI (Single-Shot) | Agentic AI (AI-HRMS) |
| :--- | :--- | :--- |
| **Execution Pattern** | User sends a prompt $\rightarrow$ Model returns text. | User defines a high-level goal $\rightarrow$ System autonomously devises and runs a multi-step execution plan. |
| **Tool Usage** | Isolated; can only output text or code snippets. | **Tool-Augmented**: Calls specialized tools (resume parsers, database retrievers, policy checkers, notification systems). |
| **Quality Verification** | Accepts output as-is, risking hallucinated data. | **Self-Reflection**: Cross-verifies extracted data against source documents before saving. |
| **Resilience** | Crashes or returns canned text on network timeouts. | **Bounded Retry**: Recovers from transient API errors with exponential backoff and jitter (`max_retries=3`). |
| **Decision Authority** | Unchecked or purely manual. | **Human-in-the-Loop (HITL)**: Proposes sensitive actions to a manager approval queue with full audit trails. |
| **Telemetry** | No execution tracking. | Tracks `trace_id`, per-step latency (ms), token consumption, and estimated USD cost. |

---

## 🏛️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            React 19 Frontend                                │
│        (Dashboard • Employees • Attendance • Leave • Payroll • Agentic Hub) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ JWT Bearer Authentication
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Django REST Framework API Gateway                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agentic AI Orchestration Engine                     │
│                                                                             │
│  ┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐  │
│  │ 1. Dynamic       │────►│ 2. Tool Execution   │────►│ 3. Bounded Retry │  │
│  │    Planner       │     │    Registry         │     │    Policy        │  │
│  └──────────────────┘     └─────────────────────┘     └────────┬─────────┘  │
│                                                                │            │
│  ┌──────────────────┐     ┌─────────────────────┐              │            │
│  │ 5. Human-in-the- │◄────│ 4. Grounded         │◄─────────────┘            │
│  │    Loop (HITL)   │     │    Reflection       │                           │
│  └────────┬─────────┘     └─────────────────────┘                           │
│           │                                                                 │
│           │ Approved                                                        │
│           ▼                                                                 │
│  ┌──────────────────────────────────────────────┐                           │
│  │ Model Updates (PostgreSQL Database)          │                           │
│  └──────────────────────────────────────────────┘                           │
│                                                                             │
│  Telemetry Logger ────► Persists AgentRun, AgentStepLog, and AuditLog       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 The 3 Autonomous Workflow Agents

AI-HRMS includes three high-level autonomous workflow agents managed by the `AgentOrchestrator`:

### 1. Autonomous Recruitment Pipeline Agent (`RECRUITMENT_PIPELINE`)
Automates the initial hiring lifecycle for new applicants:
1. **Candidate Discovery**: Identifies all un-evaluated applicants who submitted resumes for a specific job opening.
2. **Resume Screening**: Parses resume text and compares candidate skills against the job description.
3. **Anti-Hallucination Reflection**: Re-inspects the match output. If any skill was attributed to the candidate that does not exist in the resume text, it is purged and the score is recalculated.
4. **Conditional Interview Question Generation**: If the candidate's verified match score is $\ge 50\%$, the agent invokes the `InterviewPlannerTool` to write role-specific voice interview questions tailored to the candidate's skill gaps.
5. **Human-in-the-Loop Proposal**: Enqueues candidate shortlisting in the manager's review queue.

### 2. Autonomous Leave & Attendance Auditor Agent (`LEAVE_AUDIT`)
Automates policy compliance checks for all pending leave requests:
1. **Attendance History Audit**: Evaluates the requesting employee's last 30 days of attendance and computes their presence and punctuality percentage.
2. **Team Capacity & Concurrency Analysis**: Checks how many other colleagues in the same department are scheduled for leave during the requested dates to avoid understaffing.
3. **Policy Enforcement**: If attendance is $< 60\%$ or more than 2 colleagues are already away, the agent recommends **Reject Leave** with a documented explanation. Otherwise, it recommends **Approve Leave**.
4. **Manager Staging**: Places the justified recommendation in the approval queue so managers can review and confirm with one click.

### 3. Natural Language HR Copilot (`CUSTOM_INSTRUCTION`)
An interactive problem-solving agent that executes free-form operational instructions:
- **Example Prompts**:
  - *"Audit all pending leaves this week and explain any risky absences"*
  - *"Screen all candidates for Senior Python Developer and generate interview questions"*
  - *"Check company headcount and active job openings"*
- **How it works**: Uses dynamic planning to break down the natural language prompt into an executable sequence of tools, runs each step, measures latency and tokens, and logs the full execution trace.

---

## 🛠️ The 7 Functional Tool Agents

Located in `backend/agentic/tools/registry.py`, all tools implement the standard `BaseAgentTool` interface:

| Tool Name | Parameters | Purpose | HITL Required? |
| :--- | :--- | :--- | :---: |
| **`ResumeScreeningTool`** | `candidate_id`, `job_opening_id` | Extracts text from PDF resumes, extracts candidate skills, and computes fit percentage against job requirements. | No |
| **`InterviewPlannerTool`** | `candidate_id`, `count` | Formulates role-tailored voice interview questions targeting candidate skill gaps identified during screening. | No |
| **`LeaveAuditTool`** | `leave_request_id` | Calculates 30-day attendance ratio and departmental overlap conflicts to produce an approval recommendation. | No |
| **`EmployeeDataTool`** | `user_id`, `query` | Queries employee records, payroll histories, and departmental data via semantic search (ChromaDB) and database lookups. | No |
| **`CandidateStatusUpdateTool`** | `candidate_id`, `new_status`, `reason` | Applies official recruitment status changes (`Shortlisted`, `Review`, `Rejected`). | **Yes** |
| **`LeaveStatusUpdateTool`** | `leave_request_id`, `new_status`, `comment` | Applies official leave decisions (`APPROVED`, `REJECTED`). | **Yes** |
| **`NotificationDispatchTool`** | `recipient_id`, `title`, `message` | Dispatches in-app notifications and alerts to employees, candidates, and managers. | No |

---

## 🔍 Grounded Reflection & Anti-Hallucination Engine

LLMs can occasionally hallucinate candidate skills or produce out-of-range numbers. To ensure complete enterprise trustworthiness, AI-HRMS includes the **`StepReflector`** (`backend/agentic/engine/reflection.py`):

1. **Skill Grounding Check**: Cross-references every skill in `matched_skills` against the candidate's actual extracted resume text. If a skill was not in the resume, the reflection engine removes it, adjusts the match score, and logs an explanation.
2. **Score Range Clamping**: Enforces that all numerical scores strictly fall within `[0, 100]`.
3. **Labor & Ethical Compliance**: Checks generated interview questions against anti-bias rules. Questions inquiring into marital status, family planning, religion, age, or previous salary history are automatically discarded.
4. **Policy Consistency**: Ensures that leave recommendations mathematically align with policy rules (e.g. an employee with $< 60\%$ attendance cannot be recommended for approval).

---

## 💼 Core Operational HR Modules

Beyond Agentic AI, the platform provides a complete enterprise HR management suite:

1. **Employee Management**: Master records, contact info, designations, departments, manager hierarchies, and document uploads.
2. **Attendance Tracking**: Real-time daily check-in and check-out, working hours calculation, and status classification (`PRESENT`, `ABSENT`, `LATE`, `HALF_DAY`).
3. **Leave Management**: Employee leave requests, automatic balance tracking, AI recommendations, and manager approval workflows.
4. **Payroll Processing**: Automated calculation of basic salary, allowances, deductions, and tax withholdings. Includes **one-click PDF payslip generation** via ReportLab.
5. **Performance Appraisals**: Multi-criteria evaluation combining attendance scores, task delivery, manager ratings, and AI-generated performance feedback.
6. **Recruitment & Applicant Tracking**: Job postings, job description parsing, bulk resume uploads, and candidate tracking pipelines.
7. **AI Voice Interview**: Candidates can answer interview questions spoken aloud by an AI interviewer with automated speech recognition, answer evaluation, and final scoring.
8. **RAG HR Chatbot**: An in-app assistant powered by per-user ChromaDB vector stores, enabling employees to ask questions about company policies, leave rules, and personal records with cited sources.
9. **Analytics Dashboard**: Visual summaries of department distributions, attrition risks, and workforce sentiment using Recharts.

---

## 👥 Role-Based Access Control (RBAC) Matrix

Access is enforced server-side using Django REST Framework permission classes:

| Role | Dashboard | Employees | Attendance | Leave | Payroll | Performance | Recruitment | Agentic Hub | HR Chatbot |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ADMIN`** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **`SENIOR_MANAGER`** | ✅ View | ✅ View | ✅ View | ✅ Approve | ✅ View | ✅ Review | ✅ View | ✅ Full | ✅ Full |
| **`HR_RECRUITER`** | ✅ View | ✅ Full | ✅ View | ✅ View | ✅ View | ✅ View | ✅ Full | ✅ Full | ✅ Full |
| **`EMPLOYEE`** | ✅ Self | ❌ | ✅ Self | ✅ Self | ✅ Self | ✅ Self | ❌ | ❌ | ✅ Self |
| **`CANDIDATE`** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Apply | ❌ | ❌ |

---

## 🛠️ Tech Stack & Dependencies

### Backend
- **Core**: Django 5.1, Django REST Framework (DRF)
- **Authentication**: `djangorestframework-simplejwt`
- **Database**: PostgreSQL
- **AI & LLM**: OpenAI / Azure OpenAI API, Ollama (local fallback)
- **Vector Search (RAG)**: ChromaDB (`chromadb.PersistentClient`)
- **Speech & Audio**: OpenAI Whisper, Web Speech API
- **Document Processing**: ReportLab (PDF payslips), PyPDF (resume parsing)

### Frontend
- **Framework**: React 19, TypeScript, Vite
- **Styling**: Tailwind CSS with custom glassmorphic design tokens
- **Data Visualization**: Recharts
- **Icons**: Lucide React
- **HTTP Client**: Axios with Bearer token interceptor

---

## ⚡ Step-by-Step Installation & Setup Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** (LTS)
- **PostgreSQL** (running locally or via Docker)

---

### Step 1: Clone the Repository
```powershell
git clone https://github.com/manikya456/agentic_HRMS.git
cd agentic_HRMS
```

---

### Step 2: Backend Setup (Django)

1. Navigate to the backend directory:
   ```powershell
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install required Python packages:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure your environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```
   *Edit `.env` if you need custom database credentials or OpenAI API keys.*

5. Apply database migrations:
   ```powershell
   python manage.py migrate
   ```

6. Run the automated test suite to verify the agentic architecture:
   ```powershell
   python manage.py test agentic
   ```

7. Start the backend development server:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```
   *The backend API will be live at: `http://127.0.0.1:8000/api`*

---

### Step 3: Frontend Setup (React)

1. Open a new terminal window and navigate to the frontend directory:
   ```powershell
   cd frontend
   ```

2. Install frontend dependencies:
   ```powershell
   npm install
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```
   *The frontend application will be live at: `http://localhost:5173`*

---

### Step 4: Access the Application
1. Open your browser and navigate to: **`http://localhost:5173`**
2. Log in using your HR or Admin credentials.
3. In the sidebar, click on **Agentic AI** to launch automated workflows, inspect execution traces, and approve pending actions.

---

## 📡 REST API Endpoint Reference

### Agentic AI Endpoints (`/api/agentic/`)

| Method | Endpoint | Description | Permitted Roles |
| :---: | :--- | :--- | :---: |
| `POST` | `/api/agentic/runs/` | Launches an autonomous workflow or natural language copilot task | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/runs/` | Lists past agent execution runs with summary telemetry | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/runs/<trace_id>/` | Retrieves the full execution trace, step logs, outputs, and reflection critiques | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/pending-actions/` | Lists actions staged in the Human-in-the-Loop review queue | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `POST` | `/api/agentic/pending-actions/<id>/decision/` | Approves or rejects a staged action proposal | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/metrics/` | Returns aggregated metrics: average latency, token counts, USD cost, and reflection scores | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/audit-logs/` | Queries immutable system audit logs | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |
| `GET` | `/api/agentic/tools/` | Returns all registered tools, descriptions, and input schemas | `ADMIN`, `SENIOR_MANAGER`, `HR_RECRUITER` |

---

## 🧪 Testing & Quality Assurance

Run the automated backend test suite using Django's test runner:

```powershell
python manage.py test agentic
```

### Verified Test Cases:
- **`test_tool_registry_registration`**: Verifies that all 7 tools are correctly registered and adhere to parameter schema specifications.
- **`test_reflection_clamps_and_detects_hallucinations`**: Verifies that out-of-range match scores are clamped to `[0, 100]` and ungrounded skills are eliminated.
- **`test_planner_creates_recruitment_workflow`**: Verifies that the dynamic planner correctly constructs multi-step DAG plans with conditional branching.
- **`test_orchestrator_runs_and_generates_traces`**: Confirms end-to-end execution, trace generation, token tracking, and audit log creation.

---

## 🔒 Security, Privacy & Responsible AI

1. **Human-in-the-Loop Governance**: The AI system acts in an advisory capacity for high-impact decisions. Final candidate shortlisting and leave approval decisions always require explicit human sign-off.
2. **Anti-Bias & Ethical Guardrails**: Interview question generation prompts explicitly prohibit queries regarding protected attributes, marital status, family planning, age, or past compensation history.
3. **Deterministic Local Fallbacks**: If external LLM or embedding providers are unreachable, the system automatically degrades to deterministic rule-based algorithms.
4. **Audit Trail**: Every automated agent run and human review decision is immutably recorded in the `AuditLog` model with timestamps, actor IDs, and payload snapshots.

---

<div align="center">
  <b>AI-HRMS</b> — Engineered for Modern, Transparent, and Intelligent Human Resource Management.
</div>
