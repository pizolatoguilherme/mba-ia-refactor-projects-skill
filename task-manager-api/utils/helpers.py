import re


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$', email))
