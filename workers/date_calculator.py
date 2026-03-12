"""Date Calculator Agent - Port 8214"""
from datetime import datetime, timedelta
from base_worker import create_worker_app


def _parse_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def _business_days(a, b):
    start, end = min(a, b), max(a, b)
    days = 0
    current = start
    while current < end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def date_diff(payload: dict) -> dict:
    a = _parse_date(payload.get("date_a", ""))
    b = _parse_date(payload.get("date_b", ""))
    delta = abs(b - a)
    total_days = delta.days
    return {
        "days": total_days, "weeks": round(total_days / 7, 1),
        "months": round(total_days / 30.44, 1), "years": round(total_days / 365.25, 2),
        "hours": total_days * 24, "business_days": _business_days(a, b),
    }


def add_to_date(payload: dict) -> dict:
    date = _parse_date(payload.get("date", ""))
    add = payload.get("add", {})
    days = add.get("days", 0)
    months = add.get("months", 0)
    years = add.get("years", 0)
    new_month = date.month + months
    new_year = date.year + years + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    try:
        result = date.replace(year=new_year, month=new_month)
    except ValueError:
        import calendar
        last_day = calendar.monthrange(new_year, new_month)[1]
        result = date.replace(year=new_year, month=new_month, day=min(date.day, last_day))
    result += timedelta(days=days)
    return {"result_date": result.strftime("%Y-%m-%d"), "original": payload.get("date", "")}


def format_date(payload: dict) -> dict:
    date = _parse_date(payload.get("date", ""))
    fmt = payload.get("format", "ISO")
    formats = {
        "ISO": date.strftime("%Y-%m-%d"),
        "US": date.strftime("%m/%d/%Y"),
        "EU": date.strftime("%d/%m/%Y"),
        "relative": _relative(date),
    }
    result = formats.get(fmt, formats["ISO"])
    return {"formatted": result, "format": fmt}


def _relative(date):
    now = datetime.now()
    delta = now - date
    days = abs(delta.days)
    suffix = "ago" if delta.total_seconds() > 0 else "from now"
    if days == 0: return "today"
    if days == 1: return "yesterday" if suffix == "ago" else "tomorrow"
    if days < 7: return f"{days} days {suffix}"
    if days < 30: return f"{days // 7} weeks {suffix}"
    if days < 365: return f"{days // 30} months {suffix}"
    return f"{days // 365} years {suffix}"


app = create_worker_app("date-calculator", {
    "date-diff": date_diff,
    "add-to-date": add_to_date,
    "format-date": format_date,
})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8214)
