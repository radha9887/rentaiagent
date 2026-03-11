"""Code Analyzer Agent - Port 8203"""
import re
from base_worker import create_worker_app

LANG_PATTERNS = {
    "python": (r'\b(def |class |import |from .+ import|if __name__|print\()', 0.9),
    "javascript": (r'\b(function |const |let |var |=>|console\.log|require\()', 0.85),
    "java": (r'\b(public class |private |protected |System\.out|void )', 0.85),
    "rust": (r'\b(fn |let mut |impl |pub fn |println!)', 0.85),
    "go": (r'\b(func |package |import \(|fmt\.)', 0.85),
    "c": (r'#include\s*<|int main\s*\(|printf\s*\(', 0.8),
    "ruby": (r'\b(def |end$|puts |require |class .+ < )', 0.8),
}


def count_lines(payload: dict) -> dict:
    code = payload.get("code", "")
    lines = code.split("\n")
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*")))
    return {"total_lines": total, "code_lines": total - blank - comment, "blank_lines": blank, "comment_lines": comment}


def detect_language(payload: dict) -> dict:
    code = payload.get("code", "")
    best_lang, best_conf, best_count = "unknown", 0.0, 0
    for lang, (pattern, base_conf) in LANG_PATTERNS.items():
        matches = len(re.findall(pattern, code, re.MULTILINE))
        if matches > best_count:
            best_lang, best_conf, best_count = lang, base_conf, matches
    if best_count == 0:
        return {"language": "unknown", "confidence": 0.0}
    return {"language": best_lang, "confidence": round(best_conf, 2)}


def find_functions(payload: dict) -> dict:
    code = payload.get("code", "")
    functions = []
    for i, line in enumerate(code.split("\n"), 1):
        # Python
        m = re.match(r'\s*def\s+(\w+)\s*\(([^)]*)\)', line)
        if m:
            params = [p.strip().split(":")[0].split("=")[0].strip() for p in m.group(2).split(",") if p.strip()]
            functions.append({"name": m.group(1), "line": i, "params": params})
            continue
        # JS/TS
        m = re.match(r'\s*(?:function|async function)\s+(\w+)\s*\(([^)]*)\)', line)
        if m:
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            functions.append({"name": m.group(1), "line": i, "params": params})
    return {"functions": functions}


app = create_worker_app("code-analyzer", {
    "count-lines": count_lines,
    "detect-language": detect_language,
    "find-functions": find_functions,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8203)
