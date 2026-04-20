#!/usr/bin/env python
"""
Debug script to see the raw LLM responses before parsing.
This helps identify why the parser is failing.
"""

import os
import json
from dotenv import load_dotenv
from llm_client import GeminiClient

load_dotenv()

def debug_analyzer_output():
    """Capture what the LLM actually returns for analysis."""
    print("=" * 70)
    print("DEBUGGING LLM ANALYZER OUTPUT")
    print("=" * 70)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found!")
        return
    
    client = GeminiClient()
    code_sample = """def greet(name):
    print("Hello", name)
    print("Welcome!")
    return True
"""
    
    system_prompt = (
        "You are BugHound, a careful code analysis agent. "
        "Return ONLY valid JSON. No markdown, no backticks."
    )
    user_prompt = (
        "Analyze this Python code for potential issues. "
        "Return a JSON array of issue objects with keys: type, severity, msg.\n\n"
        f"CODE:\n{code_sample}"
    )
    
    print("\n[SYSTEM PROMPT]")
    print(system_prompt)
    print("\n[USER PROMPT]")
    print(user_prompt[:200] + "...")
    
    raw_response = client.complete(system_prompt, user_prompt)
    
    print("\n[RAW LLM RESPONSE]")
    print(repr(raw_response))  # Show exact string with escape chars
    print("\n[READABLE OUTPUT]")
    print(raw_response)
    
    # Try to parse it
    print("\n[PARSING ATTEMPT]")
    try:
        parsed = json.loads(raw_response)
        print("✓ Successfully parsed as JSON!")
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing failed: {e}")
    
    # Try extracting JSON array
    print("\n[TRYING TO EXTRACT JSON ARRAY]")
    if "[" in raw_response:
        start = raw_response.index("[")
        end = raw_response.rindex("]") + 1
        potential_json = raw_response[start:end]
        
        print(f"Found potential JSON: {potential_json[:100]}...")
        try:
            parsed2 = json.loads(potential_json)
            print("✓ Extracted JSON array parsed successfully!")
            print(json.dumps(parsed2, indent=2))
        except json.JSONDecodeError as e:
            print(f"✗ Extracted JSON failed: {e}")

def debug_fixer_output():
    """Capture what the LLM returns for code fixing."""
    print("\n\n" + "=" * 70)
    print("DEBUGGING LLM FIXER OUTPUT")
    print("=" * 70)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found!")
        return
    
    client = GeminiClient()
    code_sample = """def greet(name):
    print("Hello", name)
    return True
"""
    
    issues = [{"type": "Code Quality", "severity": "Low", "msg": "print() should use logging"}]
    
    system_prompt = (
        "You are BugHound, a careful refactoring assistant. "
        "Return ONLY the full rewritten Python code. No markdown, no backticks."
    )
    user_prompt = (
        "Rewrite the code to address the issues listed. "
        "Preserve behavior when possible. Keep changes minimal.\n\n"
        f"ISSUES (JSON):\n{json.dumps(issues)}\n\n"
        f"CODE:\n{code_sample}"
    )
    
    print("\n[SYSTEM PROMPT]")
    print(system_prompt)
    print("\n[USER PROMPT]")
    print(user_prompt[:200] + "...")
    
    raw_response = client.complete(system_prompt, user_prompt)
    
    print("\n[RAW LLM RESPONSE]")
    print(repr(raw_response[:200]))  # First 200 chars
    print("\n[READABLE OUTPUT (first 500 chars)]")
    print(raw_response[:500])
    
    print("\n[RESPONSE LENGTH]")
    print(f"Total chars: {len(raw_response)}")
    if not raw_response.strip():
        print("⚠️ Response is empty or whitespace only!")
    elif raw_response.startswith("```"):
        print("⚠️ Response is markdown-wrapped (starts with ```)")
    else:
        print("✓ Response looks like raw code")

if __name__ == "__main__":
    debug_analyzer_output()
    debug_fixer_output()
    print("\n\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)
