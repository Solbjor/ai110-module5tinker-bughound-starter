# BugHound Mini Model Card (Reflection)

Fill this out after you run BugHound in **both** modes (Heuristic and Gemini).

---

## 1) What is this system?

**Name:** BugHound  
**Purpose:** Analyze a Python snippet, propose a fix, and run reliability checks before suggesting whether the fix should be auto-applied.

**Intended users:** Students learning agentic workflows and AI reliability concepts.

---

## 2) How does it work?

BugHound runs a **5-step agentic workflow**:

1. **PLAN**: Decide what to analyze for (bare except, print statements, TODO comments)
2. **ANALYZE**: Detect issues in the code
   - *Heuristic mode*: Pattern matching (regex search) for known patterns
   - *Gemini mode*: Call LLM to analyze, with smart fallback to heuristics on API error
3. **ACT**: Propose a fix
   - *Heuristic mode*: Apply regex rewrites (except blocks, print→logging)
   - *Gemini mode*: Call LLM to rewrite code, fallback to heuristics if API fails
4. **TEST**: Assess risk of the proposed fix
   - Score code 0-100 based on issue severity, structural changes
   - Determine if fix is safe enough to auto-apply (guardrails)
5. **REFLECT**: Decide whether to auto-fix or defer to human
   - Auto-fix only when: risk is "low" AND no issues detected
   - Otherwise: defer to human review

The system is **gracefully degraded**: if Gemini API fails or rate-limits, the agent automatically falls back to heuristic rules without crashing.


---

## 3) Inputs and outputs

**Inputs:**

Sample code snippets tested:

1. **print_spam.py** - Simple function with print statements
   - Shape: 4 lines, single function, basic logic
   - Issue type: Code Quality (Low severity)

2. **flaky_try_except.py** - Function with bare except block
   - Shape: 7 lines, try-except, file operations
   - Issue type: Reliability (High severity)

3. **mixed_issues.py** - Function with multiple problems
   - Shape: 9 lines, nested try-except, TODO comment, print statements
   - Issue types: Code Quality (Low), Reliability (High), Maintainability (Medium)

4. **cleanish.py** - Well-written code with proper logging
   - Shape: 9 lines, two functions, no issues
   - Issue types: None detected

**Outputs:**

For each input, BugHound produces:

1. **Issues List** [{type, severity, msg}}]
   - Types: Code Quality, Reliability, Maintainability
   - Severities: Low, Medium, High
   - Message: Human-readable explanation

2. **Fixed Code** (string)
   - Heuristic fixes: regex replacements for specific patterns
   - Imports added when needed (e.g., add logging when replacing print)
   - May be identical to original if no fix available

3. **Risk Report** {score, level, reasons, should_autofix}
   - Score: 0-100 (100 = safest)
   - Level: "low" (≥75), "medium" (40-74), "high" (<40)
   - Reasons: List of why score was deducted
   - should_autofix: Boolean (True only when level=="low" AND issues==0)

---

## 4) Reliability and safety rules

**Rule 1: Issue Severity Penalty**  
Located: assess_risk(), lines 35-45

*What it checks:*
- Counts high/medium/low severity issues
- Deducts score: High=-40, Medium=-20, Low=-5
- Message: "X severity issue detected"

*Why it matters:*
- Severity indicates risk: high severity issues should prevent auto-fix
- Without this, code with critical problems might be auto-changed

*False positives:*
- The heuristic analyzer is conservative: flags all print() statements as "Low" Code Quality
- This means clean, working code with logging might still get -5 penalty if logged messages contain "print" word
- A function that prints debugging info gets flagged even though printing is appropriate in scripts

*False negatives:*
- The heuristic can't detect complex logic errors (e.g., off-by-one in loops)
- Doesn't detect security issues (e.g., eval(), SQL injection)
- Only catches hardcoded patterns, not semantic problems

---

**Rule 2: Return Statement Tracking**  
Located: assess_risk(), lines 50-55 (improved in Part 3)

*What it checks:*
- Counts "return" statements using regex: r'^return\s'
- Deducts -10 if original has more returns than fixed code
- Message: "Return statements reduced from X to Y. Verify behavior is preserved."

*Why it matters:*
- Removing returns can change program behavior (early exit)
- This rule catches destructive edits that might break logic

*False positives (with improved version):*
- None: the improved version counts actual returns, not substring "return"
- Only penalizes when returns actually decrease

*False negatives:*
- Doesn't catch if control flow is preserved but return is moved
- Generator refactoring (yield instead of return) is marked as risky but may be safe
- Doesn't detect if the fix falls off end of function (implicit return None)

---

**Rule 3 (Bonus): Auto-fix Policy Guardrail**  
Located: assess_risk(), line 117

*What it checks:*
- requires both conditions: level=="low" AND len(issues)==0
- Only auto-fixes when risk is low AND code has no detected issues

*Why it matters:*
- Prevents "unsafe confidence": auto-fixing code with problems
- Even Low severity issues need human review before changing code

*False positives:*
- Code that's already clean but has misleading log messages might be flagged
- Future heuristics might over-flag benign patterns

*False negatives:*
- Conservative: might require human review for safe simplifications
- Prevents some useful auto-fixes (e.g., removing unused variables)

---

## 5) Observed failure modes

**Failure Mode 1: Unsafe Confidence with Low Severity Issues**

*Example code:*
```python
def report(x, y):
    print(x)
    print(y)
    print(x + y)
    return x + y
```

*What went wrong:*
- BugHound detected 1 Code Quality issue (print statements)
- Risk score: 95 (low risk)
- **Auto-fix decision: True** (UNSAFE!)
- The agent wanted to auto-modify code with a detected problem

*Root cause:*
- Original auto-fix policy was: `should_autofix = (level == "low")`
- Only checked risk level, not whether issues existed

*How it was fixed:*
- Added guardrail: `should_autofix = (level == "low" and len(issues) == 0)`
- Now only auto-fixes when code is already clean
- Same code now gets auto-fix: False (safe!)

---

**Failure Mode 2: Nested Exception Detection Blindness**

*Example code:*
```python
def outer():
    try:
        def inner():
            try:
                return 1
            except:              # Bare except #1 - MISSED
                return 0
        return inner()
    except:                      # Bare except #2 - FOUND
        return None
```

*What went wrong:*
- BugHound found only 1 bare except block (the outer one)
- Missed the inner bare except block
- Issues detected: 1 (should be 2)

*Root cause:*
- Heuristic analyzer uses simple regex: `r"\bexcept\s*:\s*(\n|#|$)"`
- Pattern doesn't account for nested function definitions
- Doesn't track indentation or scope properly

*Impact:*
- Under-reports issues in complex code
- Risk score might be too optimistic for nested code

*Would require:*
- AST parsing instead of regex
- Or regex improvement to track nesting levels
- Not implemented in this version

---

**Failure Mode 3: Empty File Edge Case**

*Example code:* (empty file)

*What went wrong:*
- Empty file gets score: 0
- Risk level: high
- Auto-fix: False
- Expected: clean file (score 100, auto-fix True)

*Root cause:*
- Empty file has no fixed_code.strip() content
- First check in assess_risk: if not fixed_code.strip() → return score=0
- This is intended for "fix failed" cases, but empty code isn't a failure

*Impact:*
- Harmless but unintuitive
- User might think empty file is "high risk"

---

## 6) Heuristic vs Gemini comparison

**Test conditions:**
- Gemini API quota exhausted after testing (20-request limit)
- Agent correctly detected API errors and fell back to heuristics
- Below comparison is based on heuristic-only runs

**What both modes detected (identical):**

All four sample files produced identical issue lists:
- print_spam.py: 1 Code Quality (Low) issue
- flaky_try_except.py: 1 Reliability (High) issue  
- mixed_issues.py: 3 issues total (Code Quality, Reliability, Maintainability)
- cleanish.py: 0 issues

This is because Gemini API failure triggered fallback to _heuristic_analyze().

**Expected differences (if quota available):**

Gemini would likely detect:
- More nuanced issues (e.g., whether print is in test vs production code)
- Semantic problems (e.g., logic errors, off-by-one)
- Context-aware severity (e.g., print in logging function vs random script)

Heuristics can only:
- Match hardcoded patterns
- Apply regex-based rules
- No semantic understanding

**Proposed fixes:**

Both produced similar fixes:
- Heuristic: exact regex replacements (print → logging)
- Gemini (fallback): same, via heuristic_fix()

**Risk scores:**

Both agreed on risk levels. Example:
- print_spam.py: Low risk (score ~95), Low severity
- flaky_try_except.py: Medium/High risk (score ~25-55), High severity
- cleanish.py: Low risk (score 100), no issues

**Reliability observations:**

Heuristic mode:
- Pros: Fast, predictable, no API costs
- Cons: Limited pattern detection, no semantic understanding

Gemini mode fallback:
- Pros: Better pattern coverage when API available, graceful degradation
- Cons: Rate-limited (20 requests), requires API key

---

## 7) Human-in-the-loop decision

**Scenario where auto-fix should be refused:**

Code with High severity issues, e.g.:
```python
def process_data(config):
    try:
        return dangerous_operation(config)
    except:                    # Bare except: HIGH severity
        print("Error")
        return None            # Silent failure masks the problem
```

**Why human review is essential:**
- High severity "bare except" masks exceptions
- Fixing this changes error handling behavior
- Silent failure might hide data corruption or security issues
- Needs human judgment on what exception handling is appropriate

**Trigger to add:**
```python
if any(issue.get("severity") == "High" for issue in issues):
    should_autofix = False  # Require human review
```

**Where to implement:**
- Location: reliability/risk_assessor.py, in auto-fix policy section
- Before line 117 (current should_autofix assignment)

**Message to user:**
```
High-severity issues detected. This fix should be reviewed by a human.

- High severity issues often affect behavior or safety
- Auto-application could introduce subtle bugs
- Please review the proposed changes carefully

Risk level: HIGH | Score: 15
Auto-fix disabled: Human review required
```

**Implementation approach:**

Option 1 (Minimal): Add severity filter
```python
has_high_severity = any(
    issue.get("severity", "").lower() == "high" 
    for issue in issues
)
should_autofix = level == "low" and len(issues) == 0 and not has_high_severity
```

Option 2 (Detailed): Different thresholds for different severities
```python
if has_high_severity:
    should_autofix = False  # Never auto-fix High severity
elif has_medium_severity:
    should_autofix = (level == "low" and len(issues) == 1)  # Very conservative
else:
    should_autofix = (level == "low" and len(issues) == 0)   # Current policy
```

---

## 8) Improvement idea

**Improvement: Tighten Auto-Fix Policy with Issue Count Guardrail**

*Status: IMPLEMENTED in Part 4*

**The problem it solves:**
- Low severity issues (like print statements) were triggering auto-fix
- Code with detected problems was being modified without human review
- Example: print_spam.py with 1 issue was getting auto-fixed (unsafe)

**The change:**
```python
# Before:
should_autofix = level == "low"

# After:
should_autofix = level == "low" and len(issues) == 0
```

**Why this works:**
- Auto-fix only approved when BOTH conditions met:
  1. Risk assessment is "low" (score >= 75)
  2. NO issues were detected in analysis
- This ensures auto-apply only happens on already-clean code

**Complexity:** Very low - one line change + one conditional

**Impact:**
- Prevents unsafe confidence in modifying code with issues
- Makes decision-making more conservative and predictable
- Test shows: print_spam.py now correctly gets auto-fix=False
- All existing tests still pass

**Trade-off:**
- Conservative: might skip some safe auto-fixes
- Example: code with 1 Low severity issue won't auto-fix even if fix is safe
- But this is the right trade-off: "when in doubt, ask a human"

**Test coverage:**
Added two new tests:
1. `test_guardrail_no_autofix_with_low_severity_issues`
   - Verifies code with Low severity issues won't auto-fix
2. `test_guardrail_autofix_only_when_zero_issues`
   - Verifies clean code still gets approved for auto-fix

Both tests pass, confirming the guardrail works correctly.

---

**Alternative improvements (not implemented):**

1. **Multi-level severity handling**
   - High severity: always require human
   - Medium: more conservative
   - Low: current policy

2. **Return statement detection improvement**
   - Already improved in Part 3 (count actual returns, not substring)
   - Reduces false positives on return-related changes

3. **Confidence scores with uncertainty**
   - Instead of binary auto-fix, show "confidence: 65%"
   - Let human make final call with more information

4. **Diff visualization**
   - Show unified diff in UI
   - More transparent what's changing

5. **Heuristic pattern expansion**
   - Detect more issue types (security, performance)
   - Better nested structure detection (AST instead of regex)
