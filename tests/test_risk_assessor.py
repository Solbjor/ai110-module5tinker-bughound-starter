from reliability.risk_assessor import assess_risk


def test_no_fix_is_high_risk():
    risk = assess_risk(
        original_code="print('hi')\n",
        fixed_code="",
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print"}],
    )
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert risk["score"] == 0


def test_low_risk_when_minimal_change_and_low_severity():
    original = "import logging\n\ndef add(a, b):\n    return a + b\n"
    fixed = "import logging\n\ndef add(a, b):\n    return a + b\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "minor"}],
    )
    assert risk["level"] in ("low", "medium")  # depends on scoring rules
    assert 0 <= risk["score"] <= 100


def test_high_severity_issue_drives_score_down():
    original = "def f():\n    try:\n        return 1\n    except:\n        return 0\n"
    fixed = "def f():\n    try:\n        return 1\n    except Exception as e:\n        return 0\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Reliability", "severity": "High", "msg": "bare except"}],
    )
    assert risk["score"] <= 60
    assert risk["level"] in ("medium", "high")


def test_missing_return_is_penalized():
    original = "def f(x):\n    return x + 1\n"
    fixed = "def f(x):\n    x + 1\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[],
    )
    assert risk["score"] < 100
    assert any("Return" in r or "return" in r for r in risk["reasons"])


def test_guardrail_no_autofix_with_low_severity_issues():
    """
    GUARDRAIL TEST: Code with issues should NOT auto-fix, even if Low severity.
    
    This prevents "unsafe confidence" where the agent auto-applies changes to code
    that has problems. Even Low severity issues (like print statements) should
    require human review.
    
    Before: should_autofix = (level == "low")
    After: should_autofix = (level == "low" and len(issues) == 0)
    """
    code_with_prints = "def greet():\n    print('hello')\n    return True\n"
    fixed_with_logging = "import logging\n\ndef greet():\n    logging.info('hello')\n    return True\n"
    
    # Code with print issue detected (Low severity)
    risk = assess_risk(
        original_code=code_with_prints,
        fixed_code=fixed_with_logging,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "Found print statements"}],
    )
    
    # Risk level should be low (only Low severity issue)
    assert risk["level"] == "low"
    assert risk["score"] >= 75
    
    # BUT should NOT auto-fix just because level is low
    # The guardrail requires NO issues detected to auto-fix
    assert risk["should_autofix"] is False, (
        "GUARDRAIL FAILED: Code with Low severity issues should NOT auto-fix. "
        "Even Low severity problems need human review."
    )


def test_guardrail_autofix_only_when_zero_issues():
    """
    GUARDRAIL TEST: Auto-fix should only happen when code is already clean.
    
    When no issues are detected AND risk is low, then auto-fix is safe.
    This ensures we only modify code that has no detected problems.
    """
    clean_code = "import logging\n\ndef add(a, b):\n    return a + b\n"
    
    # No issues detected, no changes needed
    risk = assess_risk(
        original_code=clean_code,
        fixed_code=clean_code,
        issues=[],  # Empty: no issues detected
    )
    
    assert risk["level"] == "low"
    assert risk["score"] == 100
    
    # This SHOULD auto-fix (actually do nothing, but approve it)
    assert risk["should_autofix"] is True, (
        "GUARDRAIL CONSISTENCY: Clean code with no issues should be approved for auto-fix."
    )
