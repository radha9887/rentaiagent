"""Regex Generator — describe what you want to match, get a tested regex."""

import re
import os
import json
import urllib.request

def handle(task):
    description = task.get("payload", {}).get("description", "") or task.get("payload", {}).get("text", "")
    if not description or not description.strip():
        return {"error": "Describe what pattern you want to match in the 'description' field"}

    test_strings = task.get("payload", {}).get("test_strings", [])
    flavor = task.get("payload", {}).get("flavor", "python")  # python, javascript, etc.

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured"}

    prompt = f"""Create a regex pattern for: {description}

Flavor: {flavor}
{"Test against: " + json.dumps(test_strings) if test_strings else ""}

Return a JSON object (no markdown) with:
- "pattern": the regex pattern string
- "flags": any flags needed (e.g., "gi" for JS, "re.IGNORECASE" for Python)
- "explanation": break down each part of the regex
- "examples_match": 3 strings that SHOULD match
- "examples_no_match": 3 strings that should NOT match"""

    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a regex expert. Return ONLY valid JSON, no markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"].strip()
            # Try to parse as JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            regex_result = json.loads(content)

            # Validate the regex actually compiles (Python)
            pattern = regex_result.get("pattern", "")
            try:
                compiled = re.compile(pattern)
                regex_result["valid"] = True
                # Test against provided strings
                if test_strings:
                    regex_result["test_results"] = {s: bool(compiled.search(s)) for s in test_strings}
            except re.error as e:
                regex_result["valid"] = False
                regex_result["compile_error"] = str(e)

            return regex_result
    except json.JSONDecodeError:
        return {"pattern": content, "note": "Could not parse structured response"}
    except Exception as e:
        return {"error": f"Generation failed: {str(e)}"}
