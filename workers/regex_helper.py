"""Regex Helper Agent - Port 8209"""
import re
from base_worker import create_worker_app

COMMON_PATTERNS = {
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "Matches email addresses"),
    "phone": (r"\+?[\d\s\-\(\)]{7,15}", "Matches phone numbers"),
    "url": (r"https?://[^\s<>\"']+", "Matches HTTP/HTTPS URLs"),
    "ip": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "Matches IPv4 addresses"),
    "date": (r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b", "Matches common date formats"),
}


def test_regex(payload: dict) -> dict:
    pattern = payload.get("pattern", "")
    text = payload.get("text", "")
    flags_str = payload.get("flags", "")
    if not pattern:
        raise ValueError("No pattern provided")
    flags = 0
    if "i" in flags_str: flags |= re.IGNORECASE
    if "m" in flags_str: flags |= re.MULTILINE
    if "s" in flags_str: flags |= re.DOTALL
    matches = list(re.finditer(pattern, text, flags))
    groups = [m.groups() for m in matches] if matches else []
    return {"matches": len(matches) > 0, "count": len(matches), "groups": groups}


def extract_matches(payload: dict) -> dict:
    pattern = payload.get("pattern", "")
    text = payload.get("text", "")
    if not pattern:
        raise ValueError("No pattern provided")
    results = []
    for m in re.finditer(pattern, text):
        results.append({"match": m.group(), "start": m.start(), "end": m.end()})
    return {"matches": results, "count": len(results)}


def generate_regex(payload: dict) -> dict:
    regex_type = payload.get("type", "")
    if regex_type in COMMON_PATTERNS:
        pattern, desc = COMMON_PATTERNS[regex_type]
        return {"pattern": pattern, "description": desc, "type": regex_type}
    return {"pattern": ".*", "description": "Fallback: matches anything", "type": regex_type or "unknown"}


app = create_worker_app("regex-helper", {
    "test-regex": test_regex,
    "extract-matches": extract_matches,
    "generate-regex": generate_regex,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8209)
