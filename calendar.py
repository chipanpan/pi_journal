"""Date math for the journal's Monday-first calendar."""

from datetime import date, timedelta


def month_grid(year, month):
    """Return weeks of dates; None fills cells outside the month."""
    first = date(year, month, 1)
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    count = (next_month - first).days
    cells = [None] * first.weekday()
    cells.extend(date(year, month, day) for day in range(1, count + 1))
    cells.extend([None] * (-len(cells) % 7))
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


def change_month(day, amount):
    """Move to the same day if possible, or the month's last day."""
    total = day.year * 12 + day.month - 1 + amount
    year, zero_based_month = divmod(total, 12)
    month = zero_based_month + 1
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return date(year, month, min(day.day, last.day))
