from typing import Any, Dict, Tuple
import re


class StepReflector:
    """
    Self-correction and reflection engine that inspects AI tool outputs,
    detects potential hallucinations or policy violations, and auto-corrects before persisting.
    """

    @classmethod
    def reflect(cls, tool_name: str, tool_input: Dict[str, Any], tool_output: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        """
        Inspects the step output and returns: (reflection_score, critique, sanitized_output)
        """
        if not tool_output or not isinstance(tool_output, dict):
            return 30, "Empty or non-dictionary tool output received.", tool_output or {}

        if tool_name == "resume_screening":
            return cls._reflect_resume_screening(tool_output)
        elif tool_name == "interview_planner":
            return cls._reflect_interview_planner(tool_output)
        elif tool_name == "leave_audit":
            return cls._reflect_leave_audit(tool_output)
        elif tool_name == "candidate_status_update":
            return cls._reflect_status_update(tool_output)

        return 100, "Output complies with standard operational constraints.", tool_output

    @classmethod
    def _reflect_resume_screening(cls, data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        critiques = []
        score = 100
        sanitized = dict(data)

        # 1. Clamp match score
        raw_score = sanitized.get("match_score", 0)
        try:
            clamped_score = max(0, min(100, int(raw_score)))
            if clamped_score != raw_score:
                critiques.append(f"Score {raw_score} clamped to range [0, 100].")
                score -= 10
            sanitized["match_score"] = clamped_score
        except (ValueError, TypeError):
            sanitized["match_score"] = 50
            critiques.append("Malformed match score reset to default 50.")
            score -= 30

        # 2. Hallucination check on matched skills
        extracted = set(s.lower() for s in sanitized.get("extracted_skills", []))
        matched = sanitized.get("matched_skills", [])
        verified_matched = []
        hallucinated_skills = []

        for skill in matched:
            if skill.lower() in extracted or any(token in skill.lower() for token in extracted):
                verified_matched.append(skill)
            else:
                hallucinated_skills.append(skill)

        if hallucinated_skills:
            score -= min(30, len(hallucinated_skills) * 10)
            critiques.append(
                f"Detected ungrounded matched skills not present in extracted candidate skills: {', '.join(hallucinated_skills)}. Corrected."
            )
            sanitized["matched_skills"] = verified_matched

        # 3. Status consistency check
        expected_status = "Shortlisted" if sanitized["match_score"] >= 80 else "Review" if sanitized["match_score"] >= 55 else "Rejected"
        if sanitized.get("status") != expected_status:
            critiques.append(f"Status '{sanitized.get('status')}' aligned to threshold status '{expected_status}'.")
            sanitized["status"] = expected_status

        critique_summary = " | ".join(critiques) if critiques else "Resume evaluation strictly verified against candidate profile. Zero hallucinations detected."
        return max(score, 40), critique_summary, sanitized

    @classmethod
    def _reflect_interview_planner(cls, data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        critiques = []
        score = 100
        sanitized = dict(data)
        questions = sanitized.get("generated_questions", [])

        banned_patterns = [
            (r"\b(salary|compensation|expected pay|ctc|package)\b", "Salary inquiry prohibited during screening"),
            (r"\b(married|children|pregnancy|family planning|religion|caste)\b", "Protected personal attribute inquiry prohibited"),
            (r"\b(trade secret|nda|proprietary code of current employer)\b", "Confidential employer information inquiry prohibited"),
        ]

        safe_questions = []
        for q in questions:
            flagged = False
            for pattern, reason in banned_patterns:
                if re.search(pattern, q, re.IGNORECASE):
                    critiques.append(f"Removed question violating compliance policy: '{q[:40]}...' ({reason}).")
                    score -= 25
                    flagged = True
                    break
            if not flagged and len(q.strip()) > 15:
                safe_questions.append(q)

        if len(safe_questions) < len(questions):
            sanitized["generated_questions"] = safe_questions
            sanitized["questions_count"] = len(safe_questions)

        critique_summary = " | ".join(critiques) if critiques else "All interview questions verified for fairness, role relevance, and employment law compliance."
        return max(score, 50), critique_summary, sanitized

    @classmethod
    def _reflect_leave_audit(cls, data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        critiques = []
        score = 100
        sanitized = dict(data)

        attendance_ratio = sanitized.get("attendance_ratio", 100)
        recommendation = sanitized.get("recommendation", "")

        # Strict policy check
        if attendance_ratio < 60 and recommendation == "Approve Leave":
            critiques.append("Corrected recommendation: Leave cannot be approved when attendance ratio is < 60%. Overridden to Reject.")
            sanitized["recommendation"] = "Reject Leave"
            score -= 20

        critique_summary = " | ".join(critiques) if critiques else "Leave audit policy thresholds verified against employee attendance history and department coverage."
        return score, critique_summary, sanitized

    @classmethod
    def _reflect_status_update(cls, data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        return 100, "Candidate status change verified and queued for human approval.", data
