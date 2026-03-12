"""Email Writer Agent - Port 8206"""
import re
from base_worker import create_worker_app

EMAIL_TEMPLATES = {
    "professional": {
        "subject": "Regarding: {context_short}",
        "body": "Dear Sir/Madam,\n\nI am writing to you regarding {context}.\n\nI would appreciate your prompt attention to this matter. Please do not hesitate to reach out if you require any further information.\n\nBest regards"
    },
    "casual": {
        "subject": "Hey - {context_short}",
        "body": "Hey there!\n\nJust wanted to reach out about {context}.\n\nLet me know what you think!\n\nCheers"
    },
    "followup": {
        "subject": "Following up: {context_short}",
        "body": "Hi,\n\nI wanted to follow up on our previous conversation regarding {context}.\n\nWould love to hear your thoughts when you get a chance.\n\nThank you for your time.\n\nBest regards"
    },
}

FORMAL_REPLACEMENTS = [
    (r"\bwanna\b", "want to"), (r"\bgonna\b", "going to"), (r"\bcan't\b", "cannot"),
    (r"\bdon't\b", "do not"), (r"\bwon't\b", "will not"), (r"\bkinda\b", "somewhat"),
    (r"\bgotta\b", "have to"), (r"\baren't\b", "are not"), (r"\bisn't\b", "is not"),
    (r"\bHi\b", "Dear"), (r"\bHey\b", "Dear"), (r"\bthanks\b", "thank you"),
]

CONCISE_PATTERNS = [
    (r"\bin order to\b", "to"), (r"\bat this point in time\b", "now"),
    (r"\bdue to the fact that\b", "because"), (r"\bin the event that\b", "if"),
    (r"\bfor the purpose of\b", "to"), (r"\bit is important to note that\b", "notably"),
]

FRIENDLY_REPLACEMENTS = [
    (r"\bDear Sir/Madam\b", "Hi there"), (r"\bRegards\b", "Cheers"),
    (r"\bPlease be advised\b", "Just so you know"), (r"\bI wish to inform\b", "I wanted to let you know"),
]


def write_email(payload: dict) -> dict:
    email_type = payload.get("type", "professional")
    context = payload.get("context", "your inquiry")
    template = EMAIL_TEMPLATES.get(email_type, EMAIL_TEMPLATES["professional"])
    context_short = context[:50] + "..." if len(context) > 50 else context
    subject = template["subject"].format(context=context, context_short=context_short)
    body = template["body"].format(context=context, context_short=context_short)
    return {"subject": subject, "body": body, "type": email_type}


def improve_text(payload: dict) -> dict:
    text = payload.get("text", "")
    style = payload.get("style", "formal")
    if not text:
        raise ValueError("No text provided")
    improved = text
    changes = []
    replacements = {"formal": FORMAL_REPLACEMENTS, "concise": CONCISE_PATTERNS, "friendly": FRIENDLY_REPLACEMENTS}.get(style, [])
    for pattern, replacement in replacements:
        if re.search(pattern, improved, re.IGNORECASE):
            improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
            changes.append(f"Replaced '{pattern}' with '{replacement}'")
    return {"improved_text": improved, "changes": changes, "style": style}


app = create_worker_app("email-writer", {
    "write-email": write_email,
    "improve-text": improve_text,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8206)
