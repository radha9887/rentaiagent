"""Text Translator Agent - Port 8205"""
import re
from base_worker import create_worker_app

LANG_INDICATORS = {
    "english": {"the", "is", "are", "was", "have", "has", "been", "will", "would", "could", "should", "with", "from", "this", "that", "they", "which", "their", "about"},
    "spanish": {"el", "la", "los", "las", "es", "son", "fue", "tiene", "con", "por", "para", "como", "pero", "más", "este", "esta", "estos", "donde", "cuando", "también"},
    "french": {"le", "la", "les", "est", "sont", "avec", "pour", "dans", "par", "sur", "mais", "pas", "cette", "tout", "aussi", "très", "bien", "être", "avoir", "faire"},
    "german": {"der", "die", "das", "ist", "sind", "war", "mit", "auf", "für", "ein", "eine", "nicht", "sich", "auch", "nach", "noch", "wie", "über", "aber", "oder"},
    "hindi": {"है", "हैं", "का", "की", "के", "में", "को", "से", "पर", "और", "यह", "वह", "इस", "उस", "ने", "एक", "हो", "था", "कर", "जो"},
}

CHAR_RANGES = {
    "japanese": [("\u3040", "\u309f"), ("\u30a0", "\u30ff"), ("\u4e00", "\u9fff")],
    "hindi": [("\u0900", "\u097f")],
}

ROMAN_TO_DEVANAGARI = {
    "a": "अ", "aa": "आ", "i": "इ", "ee": "ई", "u": "उ", "oo": "ऊ",
    "e": "ए", "ai": "ऐ", "o": "ओ", "au": "औ",
    "ka": "क", "kha": "ख", "ga": "ग", "gha": "घ", "na": "न",
    "cha": "च", "chha": "छ", "ja": "ज", "jha": "झ",
    "ta": "त", "tha": "थ", "da": "द", "dha": "ध",
    "pa": "प", "pha": "फ", "ba": "ब", "bha": "भ", "ma": "म",
    "ya": "य", "ra": "र", "la": "ल", "va": "व", "wa": "व",
    "sha": "श", "sa": "स", "ha": "ह",
    "kya": "क्य", "tra": "त्र", "gya": "ज्ञ", "shra": "श्र",
    "namaste": "नमस्ते", "dhanyavaad": "धन्यवाद",
}

DEVANAGARI_TO_ROMAN = {v: k for k, v in ROMAN_TO_DEVANAGARI.items()}


def detect_language(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    # Check character ranges first
    for lang, ranges in CHAR_RANGES.items():
        for lo, hi in ranges:
            if any(lo <= c <= hi for c in text):
                return {"language": lang, "confidence": 0.9, "method": "character_set"}
    # Word-based detection
    words = set(re.findall(r'\b\w+\b', text.lower()))
    scores = {}
    for lang, indicators in LANG_INDICATORS.items():
        scores[lang] = len(words & indicators)
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    conf = round(scores[best] / total, 2) if scores[best] > 0 else 0
    return {"language": best if conf > 0 else "unknown", "confidence": conf, "method": "word_frequency"}


def transliterate(payload: dict) -> dict:
    text = payload.get("text", "")
    direction = payload.get("direction", "roman_to_devanagari")
    if not text:
        raise ValueError("No text provided")
    if direction == "roman_to_devanagari":
        result = text.lower()
        # Sort by length desc for greedy matching
        for roman, dev in sorted(ROMAN_TO_DEVANAGARI.items(), key=lambda x: -len(x[0])):
            result = result.replace(roman, dev)
        return {"original": text, "transliterated": result, "direction": direction}
    else:
        result = text
        for dev, roman in sorted(DEVANAGARI_TO_ROMAN.items(), key=lambda x: -len(x[0])):
            result = result.replace(dev, roman)
        return {"original": text, "transliterated": result, "direction": direction}


app = create_worker_app("text-translator", {
    "detect-language": detect_language,
    "transliterate": transliterate,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8205)
