#!/usr/bin/env python
"""
Test script to compare Gemini mode vs. heuristic mode.
This helps us understand where the AI analyzer differs from heuristics.
"""

import os
from dotenv import load_dotenv
from bughound_agent import BugHoundAgent
from llm_client import GeminiClient

load_dotenv()

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

def test_gemini_mode():
    """Test BugHound with Gemini API."""
    print("=" * 70)
    print("TESTING BUGHOUND IN GEMINI MODE")
    print("=" * 70)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file!")
        return
    
    try:
        client = GeminiClient(model_name="gemini-2.5-flash", temperature=0.2)
    except Exception as e:
        print(f"ERROR: Failed to initialize GeminiClient: {e}")
        return
    
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
            lines = fixed_code.split('\n')[:10]
            print("Code was modified. First 10 lines:")
            for i, line in enumerate(lines, 1):
                print(f"  {i:2}: {line}")
            total_lines = len(fixed_code.split('\n'))
            if total_lines > 10:
                remaining = total_lines - 10
                print(f"  ... ({remaining} more lines)")
        else:
            print("No fix was produced.")
        
        print("\n[AGENT TRACE]")
        for log in logs:
            step = log.get("step", "?")
            msg = log.get("message", "")
            short_msg = msg[:60] + "..." if len(msg) > 60 else msg
            print(f"  {step}: {short_msg}")
        
        print("\n[KEY OBSERVATIONS]")
        print(f"  ✓ Issues found: {len(issues)}")
        print(f"  ✓ Fix produced: {'Yes' if fixed_code.strip() else 'No'}")
        print(f"  ✓ Risk level: {risk.get('level', 'unknown')}")
        print(f"  ✓ Will auto-apply: {risk.get('should_autofix', False)}")

if __name__ == "__main__":
    print("Testing up to 4 samples (staying within free-tier quota)...\n")
    test_gemini_mode()
    print("\n\n" + "=" * 70)
    print("GEMINI MODE TEST COMPLETE")
    print("=" * 70)
