"""Diff Tool Agent - Port 8212"""
import difflib
import re
from base_worker import create_worker_app


def text_diff(payload: dict) -> dict:
    a = payload.get("text_a", "")
    b = payload.get("text_b", "")
    lines_a = a.splitlines(keepends=True)
    lines_b = b.splitlines(keepends=True)
    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile="text_a", tofile="text_b"))
    additions = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    total = max(len(lines_a), len(lines_b), 1)
    unchanged = total - max(additions, deletions)
    return {"diff": "".join(diff), "additions": additions, "deletions": deletions, "unchanged_pct": round(max(0, unchanged) / total * 100, 1)}


def word_count(payload: dict) -> dict:
    text = payload.get("text", "")
    words = len(text.split())
    chars = len(text)
    sentences = len(re.split(r'[.!?]+', text.strip())) if text.strip() else 0
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    reading_time = round(words / 200, 1)
    return {"words": words, "chars": chars, "sentences": sentences, "paragraphs": paragraphs, "reading_time_min": reading_time}


def char_stats(payload: dict) -> dict:
    text = payload.get("text", "")
    return {
        "uppercase": sum(1 for c in text if c.isupper()),
        "lowercase": sum(1 for c in text if c.islower()),
        "digits": sum(1 for c in text if c.isdigit()),
        "special": sum(1 for c in text if not c.isalnum() and not c.isspace()),
        "spaces": sum(1 for c in text if c.isspace()),
        "unique_chars": len(set(text)),
    }


app = create_worker_app("diff-tool", {
    "text-diff": text_diff,
    "word-count": word_count,
    "char-stats": char_stats,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8212)
