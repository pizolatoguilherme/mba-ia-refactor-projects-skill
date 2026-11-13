from datetime import datetime, timezone


def utcnow():
    """Naive UTC datetime (keeps compatibility with existing SQLite columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
