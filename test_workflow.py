#!/usr/bin/env python
"""
Test script to evaluate BugHound's heuristic workflow without the UI.
This helps us understand:
1. Where it decides what problems exist
2. Where it decides how to change code
3. Where it checks if changes are safe
"""

from bughound_agent import BugHoundAgent
from llm_client import MockClient

# Load sample code
SAMPLES = {
    "print_spam.py": """def greet(name):
    print("Hello", name)
    print("Welcome!")
    return True
""",
    "flaky_try_except.py": """def load_data(path):
    try:
        data = open(path).read()
    except:
        return None
    return data
""",
    "mixed_issues.py": """# TODO: replace with real implementation
def compute(x, y):
    print("computing...")
    try:
        return x / y
    except:
        return 0
""",
    "cleanish.py": """import logging

def add(a, b):
    logging.info("Adding numbers")
    return a + b
""",
}

def test_heuristic_mode():
    """Test BugHound in heuristic (offline) mode."""
    print("=" * 70)
    print("TESTING BUGHOUND IN HEURISTIC MODE")
    print("=" * 70)
    
    client = MockClient()
    agent = BugHoundAgent(client=client)
    
    for sample_name, code in SAMPLES.items():
        print(f"\n\n{'--' * 35}")
        print(f"Testing: {sample_name}")
        print(f"{'--' * 35}")
        
        result = agent.run(code)
        
        # Display results
        issues = result.get("issues", [])
        fixed_code = result.get("fixed_code", "")
        risk = result.get("risk", {})
        logs = result.get("logs", [])
        
        print("\n[DETECTED ISSUES]")
        if issues:
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue['type']} ({issue['severity']})")
                print(f"   → {issue['msg']}")
        else:
            print("No issues detected.")
        
        print("\n[RISK ASSESSMENT]")
        print(f"Level: {risk.get('level', 'unknown').upper()}")
        print(f"Score: {risk.get('score', 'N/A')}")
        print(f"Auto-fix?: {risk.get('should_autofix', 'N/A')}")
        if risk.get('reasons'):
            print("Reasons:")
            for reason in risk['reasons']:
                print(f"  - {reason}")
        
        print("\n[PROPOSED FIX]")
        if fixed_code.strip():
            print("Code was modified. First 10 lines:")
            for i, line in enumerate(fixed_code.split('\n')[:10], 1):
                print(f"  {i:2}: {line}")
        else:
            print("No fix was produced.")
        
        print("\n[AGENT TRACE]")
        for log in logs:
            step = log.get("step", "?")
            msg = log.get("message", "")
            print(f"  {step}: {msg}")
        
        print("\n[KEY OBSERVATIONS]")
        print(f"  ✓ Issues found: {len(issues)}")
        print(f"  ✓ Fix produced: {'Yes' if fixed_code.strip() else 'No'  }")
        print(f"  ✓ Risk level: {risk.get('level', 'unknown')}")
        print(f"  ✓ Will auto-apply: {risk.get('should_autofix', False)}")

if __name__ == "__main__":
    test_heuristic_mode()
    print("\n\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
