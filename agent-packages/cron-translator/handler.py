"""Cron Translator — human ↔ cron expression, both directions."""

import re

DAYS = {"sunday": 0, "sun": 0, "monday": 1, "mon": 1, "tuesday": 2, "tue": 2,
        "wednesday": 3, "wed": 3, "thursday": 4, "thu": 4, "friday": 5, "fri": 5,
        "saturday": 6, "sat": 6}

MONTHS = {"january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
          "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
          "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
          "november": 11, "nov": 11, "december": 12, "dec": 12}

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

def _explain_field(field, name, labels=None):
    if field == "*":
        return f"every {name}"
    if field.startswith("*/"):
        return f"every {field[2:]} {name}s"
    if "," in field:
        parts = field.split(",")
        if labels:
            parts = [labels[int(p)] if p.isdigit() and int(p) < len(labels) else p for p in parts]
        return ", ".join(parts)
    if "-" in field:
        a, b = field.split("-", 1)
        if labels:
            a = labels[int(a)] if a.isdigit() and int(a) < len(labels) else a
            b = labels[int(b)] if b.isdigit() and int(b) < len(labels) else b
        return f"{a} through {b}"
    if labels and field.isdigit() and int(field) < len(labels):
        return labels[int(field)]
    return field

def cron_to_human(expr):
    parts = expr.strip().split()
    if len(parts) not in (5, 6):
        return f"Invalid cron expression (expected 5 or 6 fields, got {len(parts)})"

    minute, hour, dom, month, dow = parts[:5]
    
    pieces = []
    
    # Time
    if minute != "*" and hour != "*":
        h = int(hour) if hour.isdigit() else hour
        m = int(minute) if minute.isdigit() else minute
        if isinstance(h, int) and isinstance(m, int):
            ampm = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            pieces.append(f"At {h12}:{m:02d} {ampm}")
        else:
            pieces.append(f"At minute {minute} of hour {hour}")
    elif minute.startswith("*/"):
        pieces.append(f"Every {minute[2:]} minutes")
    elif hour.startswith("*/"):
        pieces.append(f"Every {hour[2:]} hours")
    else:
        pieces.append(f"Minute: {minute}, Hour: {hour}")

    # Day of week
    if dow != "*":
        pieces.append(_explain_field(dow, "day", DAY_NAMES))
    
    # Day of month
    if dom != "*":
        pieces.append(f"on day {dom} of the month")
    
    # Month
    if month != "*":
        pieces.append(f"in {_explain_field(month, 'month', MONTH_NAMES)}")

    return ", ".join(pieces)

def human_to_cron(text):
    text = text.lower().strip()
    
    minute, hour, dom, month, dow = "*", "*", "*", "*", "*"
    
    # Extract time
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', text)
    if time_match:
        h, m = int(time_match.group(1)), int(time_match.group(2))
        if time_match.group(3) == "pm" and h < 12:
            h += 12
        elif time_match.group(3) == "am" and h == 12:
            h = 0
        minute, hour = str(m), str(h)
    elif "midnight" in text:
        minute, hour = "0", "0"
    elif "noon" in text:
        minute, hour = "0", "12"
    
    # Extract interval
    every_match = re.search(r'every\s+(\d+)\s*(minute|hour|day|week|month)', text)
    if every_match:
        n, unit = every_match.group(1), every_match.group(2)
        if unit == "minute":
            minute = f"*/{n}"
        elif unit == "hour":
            minute = "0"
            hour = f"*/{n}"
    
    # Extract days
    found_days = []
    for day_name, day_num in DAYS.items():
        if day_name in text:
            found_days.append(str(day_num))
    if found_days:
        dow = ",".join(sorted(set(found_days)))
    elif "weekday" in text or "weekdays" in text:
        dow = "1-5"
    elif "weekend" in text:
        dow = "0,6"
    elif "daily" in text or "every day" in text:
        dow = "*"
    
    # Extract months
    for month_name, month_num in MONTHS.items():
        if month_name in text:
            month = str(month_num)
            break
    
    expr = f"{minute} {hour} {dom} {month} {dow}"
    return expr

def handle(task):
    payload = task.get("payload", {})
    text = payload.get("text", "") or payload.get("expression", "") or payload.get("cron", "")
    
    if not text or not text.strip():
        return {"error": "Provide a cron expression or plain English description in the 'text' field"}
    
    text = text.strip()
    
    # Detect if it's a cron expression (5-6 space-separated fields with */digits)
    parts = text.split()
    is_cron = len(parts) in (5, 6) and all(
        re.match(r'^[\d\*\/\,\-]+$', p) for p in parts[:5]
    )
    
    if is_cron:
        human = cron_to_human(text)
        return {
            "direction": "cron → human",
            "cron": text,
            "human": human,
            "next_tip": "Fields: minute hour day-of-month month day-of-week"
        }
    else:
        cron = human_to_cron(text)
        verification = cron_to_human(cron)
        return {
            "direction": "human → cron",
            "human": text,
            "cron": cron,
            "verification": verification,
            "next_tip": "Fields: minute hour day-of-month month day-of-week"
        }
