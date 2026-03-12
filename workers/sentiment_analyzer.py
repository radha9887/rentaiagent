"""Sentiment Analyzer Agent - Port 8204"""
import re
from base_worker import create_worker_app

POSITIVE_WORDS = set("good great excellent amazing wonderful fantastic awesome happy love like best beautiful brilliant perfect superb outstanding magnificent terrific fabulous delightful pleasant cheerful excited grateful thankful blessed proud confident optimistic enthusiastic joyful peaceful calm satisfied pleased impressed inspired hopeful warm kind gentle nice cool".split())
NEGATIVE_WORDS = set("bad terrible awful horrible worst hate dislike ugly stupid boring dull painful sad angry frustrated disappointed disgusted annoyed irritated furious miserable depressed anxious worried scared afraid nervous stressed upset unhappy lonely confused lost broken failed failure worthless hopeless".split())
JOY_WORDS = set("happy joy joyful delighted glad cheerful excited thrilled elated blissful ecstatic pleased grateful love wonderful amazing fantastic awesome celebrate".split())
ANGER_WORDS = set("angry furious mad rage outraged irritated annoyed frustrated infuriated livid hostile aggressive hate despise resent".split())
SADNESS_WORDS = set("sad unhappy depressed miserable gloomy heartbroken sorrowful melancholy disappointed dejected hopeless lonely grief mourning".split())
FEAR_WORDS = set("afraid scared terrified frightened anxious worried nervous panic dread horror alarmed startled uneasy apprehensive".split())
SURPRISE_WORDS = set("surprised shocked amazed astonished stunned unexpected wow unbelievable incredible astounded bewildered startled".split())


def analyze_sentiment(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    words = re.findall(r'\b[a-z]+\b', text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos + neg or 1
    if pos > neg:
        sentiment, score = "positive", round(pos / total, 2)
    elif neg > pos:
        sentiment, score = "negative", round(neg / total, 2)
    else:
        sentiment, score = "neutral", 0.5
    return {"sentiment": sentiment, "score": score, "breakdown": {"positive": pos, "negative": neg, "neutral": len(words) - pos - neg}}


def detect_emotion(payload: dict) -> dict:
    text = payload.get("text", "")
    if not text:
        raise ValueError("No text provided")
    words = set(re.findall(r'\b[a-z]+\b', text.lower()))
    emotions = {
        "joy": len(words & JOY_WORDS),
        "anger": len(words & ANGER_WORDS),
        "sadness": len(words & SADNESS_WORDS),
        "fear": len(words & FEAR_WORDS),
        "surprise": len(words & SURPRISE_WORDS),
    }
    primary = max(emotions, key=emotions.get) if any(emotions.values()) else "neutral"
    return {"primary_emotion": primary, "emotions": emotions}


app = create_worker_app("sentiment-analyzer", {
    "analyze-sentiment": analyze_sentiment,
    "detect-emotion": detect_emotion,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8204)
