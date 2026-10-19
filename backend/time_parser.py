import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_time_range(text: str, ref_time: Optional[datetime] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses natural language relative time expressions from text.
    Returns: (start_time, end_time) as ISO string '%Y-%m-%d %H:%M:%S', or (None, None).
    
    Supports:
      - last N minute(s) (e.g. 'last 5 minutes', 'last 30 mins')
      - last N hour(s) / last hour / past hour
      - last N day(s)
      - today
      - since morning
    """
    if not text:
        return None, None

    now = ref_time or datetime.now()
    t_lower = text.lower()

    # Pattern: last / past N minutes
    m_min = re.search(r'(?:last|past|in the last)\s+(\d+)\s*(?:minutes?|mins?)', t_lower)
    if m_min:
        mins = int(m_min.group(1))
        start = now - timedelta(minutes=mins)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    # Pattern: last hour / past hour
    if re.search(r'(?:last|past|in the last)\s+(?:an?\s+)?hour', t_lower) and not re.search(r'\d+\s*hours?', t_lower):
        start = now - timedelta(hours=1)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    # Pattern: last N hours
    m_hr = re.search(r'(?:last|past|in the last)\s+(\d+)\s*(?:hours?|hrs?)', t_lower)
    if m_hr:
        hrs = int(m_hr.group(1))
        start = now - timedelta(hours=hrs)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    # Pattern: today
    if "today" in t_lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    # Pattern: since morning
    if "since morning" in t_lower or "this morning" in t_lower:
        start = now.replace(hour=6, minute=0, second=0, microsecond=0)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    # Pattern: last N days
    m_day = re.search(r'(?:last|past)\s+(\d+)\s*days?', t_lower)
    if m_day:
        days = int(m_day.group(1))
        start = now - timedelta(days=days)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    return None, None


if __name__ == "__main__":
    test_phrases = [
        "What was the average temperature of Machine 2 in the last 30 minutes?",
        "Show temperature trend of machine 2 for the last hour.",
        "Check errors in the last 10 minutes",
        "How much energy was used today?",
        "Machines active since morning",
        "What is the status right now?"
    ]
    now = datetime(2026, 10, 19, 17, 0, 0)
    for p in test_phrases:
        s, e = parse_time_range(p, ref_time=now)
        print(f"'{p}' -> start={s}, end={e}")
