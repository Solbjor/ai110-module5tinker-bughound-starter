from typing import Dict, List
import re


def _count_return_statements(code: str) -> int:
    """Count actual return statements in the code.
    
    Looks for 'return' keyword at the start of a line (after whitespace).
    This avoids false positives from comments or strings.
    """
    lines = code.split('\n')
    count = 0
    for line in lines:
        stripped = line.lstrip()
        # Match 'return' as a keyword followed by space, newline, or colon
        if re.match(r'^return\s', stripped) or stripped == 'return':
            count += 1
    return count


def assess_risk(
    original_code: str,
    fixed_code: str,
    issues: List[Dict[str, str]],
) -> Dict[str, object]:
    """
    Simple, explicit risk assessment used as a guardrail layer.

    Returns a dict with:
    - score: int from 0 to 100
    - level: "low" | "medium" | "high"
    - reasons: list of strings explaining deductions
    - should_autofix: bool
    """

    reasons: List[str] = []
    score = 100

    if not fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["No fix was produced."],
            "should_autofix": False,
        }

    original_lines = original_code.strip().splitlines()
    fixed_lines = fixed_code.strip().splitlines()

    # ----------------------------
    # Issue severity based risk
    # ----------------------------
    for issue in issues:
        severity = str(issue.get("severity", "")).lower()

        if severity == "high":
            score -= 40
            reasons.append("High severity issue detected.")
        elif severity == "medium":
            score -= 20
            reasons.append("Medium severity issue detected.")
        elif severity == "low":
            score -= 5
            reasons.append("Low severity issue detected.")

    # ----------------------------
    # Structural change checks
    # ----------------------------
    if len(fixed_lines) < len(original_lines) * 0.5:
        score -= 20
        reasons.append("Fixed code is much shorter than original.")

    # IMPROVEMENT: Instead of naive "return" substring check, count actual return statements.
    # Only penalize if returns are actually removed (fewer in fixed code).
    original_returns = _count_return_statements(original_code)
    fixed_returns = _count_return_statements(fixed_code)
    
    if original_returns > 0 and fixed_returns < original_returns:
        # Penalty reduced from 30 to 10, and only applied when returns actually decrease.
        # This avoids false positives where code is optimized but still functional.
        score -= 10
        reasons.append(f"Return statements reduced from {original_returns} to {fixed_returns}. Verify behavior is preserved.")

    if "except:" in original_code and "except:" not in fixed_code:
        # This is usually good, but still risky.
        score -= 5
        reasons.append("Bare except was modified, verify correctness.")

    # ----------------------------
    # Clamp score
    # ----------------------------
    score = max(0, min(100, score))

    # ----------------------------
    # Risk level
    # ----------------------------
    if score >= 75:
        level = "low"
    elif score >= 40:
        level = "medium"
    else:
        level = "high"

    # ----------------------------
    # Auto-fix policy
    # ----------------------------
    should_autofix = level == "low"

    if not reasons:
        reasons.append("No significant risks detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "should_autofix": should_autofix,
    }
