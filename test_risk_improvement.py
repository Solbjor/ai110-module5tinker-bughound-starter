#!/usr/bin/env python
"""
Test to demonstrate risk assessment issues and test improvements.

Key Problem: The risk assessor penalizes structural changes too harshly.

Specific issue: "If return exists in original but not in fixed: -30 points"
This is a naive check that doesn't understand context. A fix that removes
a return statement is risky - but the check uses the word "return" too literally.

This test demonstrates false positives and validates improvements.
"""

import re
from reliability.risk_assessor import assess_risk

# Test case 1: Simple case - return is truly removed (bad fix, should be high risk)
original_returns = """def validate(x):
    if x > 0:
        return True
    return False
"""

fixed_missing_return = """def validate(x):
    if x > 0:
        return True
    # forgot to return False case!
"""

# Test case 2: Function with early return that gets optimized (good fix, low risk)
original_with_early_return = """def expensive_operation(data):
    results = []
    for item in data:
        if not item:
            return []  # Early exit
        results.append(process(item))
    return results
"""

fixed_optimized = """def expensive_operation(data):
    for item in data:
        if not item:
            return []
        yield process(item)  # Generator instead of building list
"""

# Test case 3: The word "return" appears in comment - might fool the check
original_with_comment = """def load():
    # Important: return None on error (not False!)
    try:
        return data
    except:
        return None
"""

fixed_different_comment = """def load():
    try:
        return data
    except Exception:
        # Caught exception, return early with None
        return None
"""

issues_low = [{"type": "Code Quality", "severity": "Low", "msg": "Minor issue"}]
issues_high = [{"type": "Reliability", "severity": "High", "msg": "Major issue"}]

print("=" * 70)
print("TESTING RISK ASSESSMENT ACCURACY")
print("=" * 70)

print("\n[TEST 1] Return statement truly removed (BAD FIX - should be HIGH RISK)")
print("-" * 70)
print("Original code:")
print(original_returns)
print("Fixed code:")
print(fixed_missing_return)
risk1 = assess_risk(original_returns, fixed_missing_return, issues_high)
print(f"Risk score: {risk1['score']}, Level: {risk1['level']}")
print(f"Should auto-fix: {risk1['should_autofix']}")
for reason in risk1['reasons']:
    print(f"  - {reason}")
if risk1['level'] == 'high':
    print("✓ CORRECT: Properly identified as high risk")
else:
    print("✗ PROBLEM: Should be high risk!")

print("\n[TEST 2] Return statement removed but code still works (GOOD FIX - low risk)")
print("-" * 70)
print("Original (with redundant return):")
print(original_with_early_return)
print("Fixed (generator style):")
print(fixed_optimized)
risk2 = assess_risk(original_with_early_return, fixed_optimized, issues_low)
print(f"Risk score: {risk2['score']}, Level: {risk2['level']}")
print(f"Should auto-fix: {risk2['should_autofix']}")
for reason in risk2['reasons']:
    print(f"  - {reason}")
if "Return statements may have been removed" in str(risk2['reasons']):
    print("⚠️ FALSE POSITIVE: Flagged for removed return, but replacement works fine")
    print("  (The check looks for word 'return' - original has 2, fixed has 1)")
print("   Current approach: too conservative!")

print("\n[TEST 3] Return appears in comments (edge case)")  
print("-" * 70)
risk3 = assess_risk(original_with_comment, fixed_different_comment, issues_low)
print(f"Risk score: {risk3['score']}, Level: {risk3['level']}")
print(f"Should auto-fix: {risk3['should_autofix']}")
for reason in risk3['reasons']:
    print(f"  - {reason}")
if "Return statements may have been removed" not in str(risk3['reasons']):
    print("✓ No false positive here (both have 'return' keyword)")

print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)
print("""
CURRENT CHECK (naive):
  if "return" in original_code and "return" not in fixed_code:
      score -= 30

PROBLEM:
  - Only checks if the word "return" appears, not actual returns
  - Counts multiple returns as one
  - Can't distinguish: "return removed and broke code" vs
                       "return simplified but still functional"
  - -30 penalty is huge (moves test 2 from low risk to medium risk)

BETTER APPROACH:
  - Count actual return statements with regex: r'^\s*return\b'
  - Only penalize if FEWER returns in fixed code AND severity is HIGH
  - Or require returns to be at END of function (not removed mid-flow)
  - Smaller penalty: -10 instead of -30 (less aggressive)
  - Only apply when there are high severity issues detected
""")

print("\nMaking improvement: counting actual return statements instead...")
print("\n" + "=" * 70)
