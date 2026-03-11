"""Text Summarizer Agent - Port 8201"""
import re
from collections import Counter
from base_worker import create_worker_app

STOP_WORDS = set("the a an is are was were be been being have has had do does did will would shall should may might can could of in to for on with at by from as into through during before after above below between out off over under again further then once here there when where why how all each every both few more most other some such no nor not only own same so than too very".split())


def summarize(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    summary = " ".join(sentences[:3]) if len(sentences) > 3 else text
    return {"summary": summary, "word_count": len(text.split()), "sentence_count": len(sentences)}


def extract_keywords(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    counts = Counter(filtered)
    keywords = [w for w, _ in counts.most_common(10)]
    return {"keywords": keywords}


app = create_worker_app("text-summarizer", {
    "summarize": summarize,
    "extract-keywords": extract_keywords,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8201)
