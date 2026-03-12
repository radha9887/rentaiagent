"""Password Generator Agent - Port 8215"""
import string
import secrets
import math
from base_worker import create_worker_app

WORD_LIST = [
    "apple", "banana", "cherry", "dragon", "eagle", "falcon", "garden", "harbor",
    "island", "jungle", "knight", "lemon", "marble", "nectar", "ocean", "palace",
    "quantum", "river", "silver", "tiger", "ultra", "violet", "willow", "xenon",
    "yellow", "zenith", "amber", "blaze", "cloud", "delta", "ember", "frost",
    "globe", "haven", "ivory", "joker", "karma", "lotus", "mystic", "noble",
    "orbit", "prism", "quest", "raven", "storm", "torch", "umbra", "vortex",
    "whale", "zephyr", "atlas", "brave", "coral", "dusk", "epoch", "flame",
    "grace", "haste", "index", "jewel", "kite", "lunar", "modal", "nexus",
]


def generate_password(payload: dict) -> dict:
    length = payload.get("length", 16)
    use_upper = payload.get("uppercase", True)
    use_lower = payload.get("lowercase", True)
    use_digits = payload.get("digits", True)
    use_special = payload.get("special", True)
    chars = ""
    if use_lower: chars += string.ascii_lowercase
    if use_upper: chars += string.ascii_uppercase
    if use_digits: chars += string.digits
    if use_special: chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    if not chars:
        chars = string.ascii_letters + string.digits
    password = "".join(secrets.choice(chars) for _ in range(length))
    entropy = round(length * math.log2(len(chars)), 1)
    return {"password": password, "entropy_bits": entropy}


def check_strength(payload: dict) -> dict:
    pw = payload.get("password", "")
    if not pw:
        raise ValueError("No password provided")
    score = 0
    suggestions = []
    if len(pw) >= 8: score += 20
    elif len(pw) >= 6: score += 10
    else: suggestions.append("Use at least 8 characters")
    if len(pw) >= 12: score += 10
    if len(pw) >= 16: score += 10
    if any(c.islower() for c in pw): score += 10
    else: suggestions.append("Add lowercase letters")
    if any(c.isupper() for c in pw): score += 10
    else: suggestions.append("Add uppercase letters")
    if any(c.isdigit() for c in pw): score += 10
    else: suggestions.append("Add digits")
    if any(not c.isalnum() for c in pw): score += 15
    else: suggestions.append("Add special characters")
    if len(set(pw)) > len(pw) * 0.6: score += 15
    else: suggestions.append("Use more unique characters")
    score = min(score, 100)
    if score >= 80: level = "very_strong"
    elif score >= 60: level = "strong"
    elif score >= 40: level = "medium"
    else: level = "weak"
    return {"score": score, "level": level, "suggestions": suggestions}


def generate_passphrase(payload: dict) -> dict:
    num_words = payload.get("words", 4)
    separator = payload.get("separator", "-")
    words = [secrets.choice(WORD_LIST) for _ in range(num_words)]
    passphrase = separator.join(words)
    entropy = round(num_words * math.log2(len(WORD_LIST)), 1)
    return {"passphrase": passphrase, "entropy_bits": entropy}


app = create_worker_app("password-generator", {
    "generate-password": generate_password,
    "check-strength": check_strength,
    "generate-passphrase": generate_passphrase,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8215)
