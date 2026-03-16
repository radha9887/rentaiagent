"""Error Explainer — paste a stack trace, get a plain English explanation + fix."""

import os
import json
import urllib.request

def handle(task):
    error = task.get("payload", {}).get("error", "") or task.get("payload", {}).get("text", "")
    if not error or not error.strip():
        return {"error": "Provide an error/stack trace in the 'error' field"}

    context = task.get("payload", {}).get("context", "")  # optional: what were you trying to do

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured"}

    prompt = f"""Analyze this error/stack trace:

```
{error}
```
{"Context: " + context if context else ""}

Provide:
1. **What happened** — one sentence, plain English
2. **Why** — root cause explanation
3. **Fix** — exact steps or code to fix it
4. **Prevention** — how to avoid this in the future

Be specific and actionable. No fluff."""

    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a senior debugger. Explain errors clearly and provide actionable fixes. Be concise and specific."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1500
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            explanation = result["choices"][0]["message"]["content"]
            return {
                "explanation": explanation,
                "tokens_used": result.get("usage", {}).get("total_tokens", 0)
            }
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
