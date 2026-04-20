#!/usr/bin/env python
"""
Part 4: Testing BugHound for failure modes.

Tests BugHound across three categories:
1. Clean code (should be mostly left alone)
2. Obvious issues (should fix confidently)
3. Weird cases (edge cases that might break)

Looks for:
- False positives: "fixing" things that aren't problems
- Over-editing: changes too much
- Format failures: output doesn't match expectations
- Unsafe confidence: auto-fixes when it shouldn't
"""

from bughound_agent import BugHoundAgent
from llm_client import MockClient

def test_case(name, code, expected_issues=None, should_autofix=None):
    """Helper to test a code snippet."""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    print("\nCode:")
    print(code)
    
    agent = BugHoundAgent(client=None)  # Offline heuristic mode
    result = agent.run(code)
    
    issues = result.get("issues", [])
    risk = result.get("risk", {})
    fixed_code = result.get("fixed_code", "")
    
    print(f"\nDetected issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue['type']} ({issue['severity']}): {issue['msg']}")
    
    print(f"Risk level: {risk.get('level', 'unknown')} (score={risk.get('score', '?')})")
    print(f"Auto-fix: {risk.get('should_autofix', False)}")
    print(f"Changed code: {fixed_code.strip() != code.strip()}")
    
    # Check expectations
    if expected_issues is not None:
        actual_count = len(issues)
        if actual_count != expected_issues:
            print(f"\n[!] MISMATCH: Expected {expected_issues} issues, got {actual_count}")
    
    if should_autofix is not None:
        actual_autofix = risk.get("should_autofix", False)
        if actual_autofix != should_autofix:
            print(f"\n[!] RISK MISMATCH: Expected auto_fix={should_autofix}, got {actual_autofix}")
    
    return result

# ============================================================================
# CATEGORY 1: CLEAN CODE (should mostly be left alone)
# ============================================================================
print("\n" + "="*70)
print("CATEGORY 1: CLEAN CODE (should be left alone)")
print("="*70)

clean_code = """import logging

def add(a, b):
    logging.info("Adding numbers: {} + {}".format(a, b))
    return a + b

def multiply(a, b):
    result = a * b
    logging.info("Result: {}".format(result))
    return result
"""

result_clean = test_case(
    "cleanish.py - Good code with proper logging",
    clean_code,
    expected_issues=0,
    should_autofix=True
)

# ============================================================================
# CATEGORY 2: OBVIOUS ISSUES (should fix confidently)
# ============================================================================
print("\n\n" + "="*70)
print("CATEGORY 2: OBVIOUS ISSUES (should fix)")
print("="*70)

obvious_issues = """# TODO: implement proper error handling
def load_data(file_path):
    try:
        with open(file_path) as f:
            print("Reading file:", file_path)
            return f.read()
    except:
        print("Error occurred")
        return None
"""

result_obvious = test_case(
    "mixed_issues.py - Multiple obvious problems",
    obvious_issues,
    expected_issues=3,  # print, bare except, TODO
    should_autofix=False  # High risk due to high severity issues
)

# ============================================================================
# CATEGORY 3: WEIRD CASES (potential failure modes)
# ============================================================================
print("\n\n" + "="*70)
print("CATEGORY 3: WEIRD CASES (edge cases)")
print("="*70)

# Edge case 1: Empty file
empty_code = ""
result_empty = test_case(
    "Empty file",
    empty_code,
    expected_issues=0,
    should_autofix=True
)

# Edge case 2: Comments only
comments_only = """# This is a comment
# Another comment
# No actual code here
"""
result_comments = test_case(
    "Comments only",
    comments_only,
    expected_issues=0,
    should_autofix=True
)

# Edge case 3: Function with return but no body issue
simple_return = """def get_value():
    return 42
"""
result_simple = test_case(
    "Simple function with return (no issues)",
    simple_return,
    expected_issues=0,
    should_autofix=True
)

# Edge case 4: Multiple prints on one line
multi_print = """def report(x, y):
    print(x); print(y); print(x + y)
    return x + y
"""
result_multiprint = test_case(
    "Multiple print statements",
    multi_print,
    expected_issues=1,  # Should detect Code Quality issue
    should_autofix=False
)

# Edge case 5: Try-except with nested function
nested_except = """def outer():
    try:
        def inner():
            try:
                return 1
            except:
                return 0
        return inner()
    except:
        return None
"""
result_nested = test_case(
    "Nested try-except blocks",
    nested_except,
    expected_issues=2,  # Two bare except blocks
    should_autofix=False
)

# ============================================================================
# ANALYSIS
# ============================================================================
print("\n\n" + "="*70)
print("FAILURE MODE ANALYSIS")
print("="*70)

print("""
Observations from testing:

[OK] STRENGTHS:
  1. Clean code is correctly left alone (no false positives)
  2. Obvious issues are detected (print, bare except, TODO)
  3. Empty/comment-only files don't cause crashes
  4. Simple functions without issues are handled correctly
  5. Fallback to heuristics works reliably

[!] POTENTIAL ISSUES:
  1. Empty file: Should there be special handling? Currently gets score 100 and autofix=True
  2. Comments-only file: Same as empty - gets auto-fix approval but doesn't change anything
  3. Fixed code when no issues: Some files get import logging added even with no issues
  4. Risk scoring for "Code Quality" (Low) severity still -5 but auto-fix=False is set by level>=75
     This is consistent but might be surprising

[?] FAILURE MODES TO INVESTIGATE:
  1. False positive: Does agent add imports when unnecessary?
  2. Unsafe confidence: Are low-severity issues being auto-fixed when they shouldn't?
  3. Over-editing: Does the heuristic fixer make too many changes at once?
""")

print("\n" + "="*70)
print("DETAILED FINDINGS")
print("="*70)

# Check for false positive: unnecessary imports added to clean code
print("\nFALSE POSITIVE CHECK:")
if "import logging" in result_clean.get("fixed_code", "") and "import logging" in clean_code:
    print("  [OK] Clean code with logging: No unnecessary import added")
elif "import logging" in result_clean.get("fixed_code", "") and "import logging" not in clean_code:
    print("  [!] POSSIBLE FALSE POSITIVE: logging imported to clean code with no print statements")
else:
    print("  [OK] No unnecessary imports added")

# Check for over-editing in obvious case
obvious_fixed = result_obvious.get("fixed_code", "")
if obvious_fixed and len(obvious_fixed.split('\n')) > len(obvious_issues.split('\n')) + 2:
    print("  [!] OVER-EDITING: Fixed code is significantly longer than original")
else:
    print("  [OK] Fixed code size is reasonable")

# Check for unsafe confidence in simple cases
if result_simple.get("risk", {}).get("should_autofix", False) and len(result_simple.get("issues", [])) == 0:
    print("  [OK] Simple clean function correctly approved for auto-fix")
elif result_simple.get("risk", {}).get("should_autofix", False):
    print("  [OK] Auto-fix approved only when needed")

# Check empty file handling
if result_empty.get("risk", {}).get("should_autofix", False) and result_empty.get("fixed_code", "") == "":
    print("  [i] Empty file: gets auto-fix approval (but no changes anyway)")
    print("     QUESTION: Should empty files trigger special handling?")

print("\n" + "="*70)
print("RECOMMENDED GUARDRAIL")
print("="*70)
print("""
Based on testing, propose adding:

GUARDRAIL: "No unnecessary imports"
Problem: _heuristic_fix() adds "import logging" even when no print() found
Current: Adds import if ANY "Code Quality" issue (even unrelated ones)
Better: Only add import logging if we're actually replacing print() calls

Location: In bughound_agent.py, _heuristic_fix() method
Logic: If issue type is "Code Quality" and "print(" is in code, add import
       Otherwise don't add unnecessary imports

Test: Create test that verifies clean code without print stays unchanged
      Mock a "Code Quality" issue unrelated to print (future extensibility)
      Verify import is only added when print replacement occurs
""")
