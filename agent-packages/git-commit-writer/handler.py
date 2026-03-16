"""Git Commit Writer — paste a diff, get a conventional commit message."""

import os
import json
import urllib.request

def handle(task):
    diff = task.get("payload", {}).get("diff", "") or task.get("payload", {}).get("text", "")
    if not diff or not diff.strip():
        return {"error": "Provide a git diff in the 'diff' field"}

    style = task.get("payload", {}).get("style", "conventional")  # conventional, simple, detailed

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured"}

    prompt = f"""Write a git commit message for this diff:

```diff
{diff[:8000]}
```

Style: {style}
{"Format: type(scope): description" if style == "conventional" else ""}

Rules:
- First line: max 72 chars
- {"Use conventional commit types: feat, fix, refactor, docs, test, chore, perf, style, ci, build" if style == "conventional" else "Be descriptive but concise"}
- Body: bullet points of what changed (if needed)
- No generic messages like "update files" or "fix bug"
- Be specific about WHAT changed and WHY

Return ONLY the commit message, nothing else."""

    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You write precise, professional git commit messages. Return ONLY the commit message."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
            message = result["choices"][0]["message"]["content"].strip()
            return {
                "commit_message": message,
                "style": style,
                "diff_lines": len(diff.splitlines()),
                "tokens_used": result.get("usage", {}).get("total_tokens", 0)
            }
    except Exception as e:
        return {"error": f"Generation failed: {str(e)}"}
