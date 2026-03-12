"""Markdown Converter Agent - Port 8210"""
import re
from base_worker import create_worker_app

try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

HTML_TO_MD_MAP = [
    (r"<h1[^>]*>(.*?)</h1>", r"# \1\n"), (r"<h2[^>]*>(.*?)</h2>", r"## \1\n"),
    (r"<h3[^>]*>(.*?)</h3>", r"### \1\n"), (r"<h4[^>]*>(.*?)</h4>", r"#### \1\n"),
    (r"<strong>(.*?)</strong>", r"**\1**"), (r"<b>(.*?)</b>", r"**\1**"),
    (r"<em>(.*?)</em>", r"*\1*"), (r"<i>(.*?)</i>", r"*\1*"),
    (r"<code>(.*?)</code>", r"`\1`"), (r"<br\s*/?>", "\n"),
    (r"<p>(.*?)</p>", r"\1\n\n"), (r"<li>(.*?)</li>", r"- \1\n"),
    (r"<a href=[\"'](.*?)[\"']>(.*?)</a>", r"[\2](\1)"),
    (r"<[^>]+>", ""),
]


def md_to_html(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    if HAS_MARKDOWN:
        html = md_lib.markdown(text)
    else:
        html = text
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    return {"html": html}


def html_to_md(payload: dict) -> dict:
    html = payload.get("html", payload.get("text", ""))
    if not html:
        raise ValueError("No HTML provided")
    result = html
    for pattern, replacement in HTML_TO_MD_MAP:
        result = re.sub(pattern, replacement, result, flags=re.DOTALL | re.IGNORECASE)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return {"markdown": result}


def format_markdown(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    lines = text.split("\n")
    formatted = []
    for line in lines:
        line = re.sub(r"^(#{1,6})([^ #])", r"\1 \2", line)
        line = re.sub(r"^[-*] {2,}", "- ", line)
        formatted.append(line)
    result = "\n".join(formatted)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return {"formatted": result.strip()}


app = create_worker_app("markdown-converter", {
    "md-to-html": md_to_html,
    "html-to-md": html_to_md,
    "format-markdown": format_markdown,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8210)
