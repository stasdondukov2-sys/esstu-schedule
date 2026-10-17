"""Group coverage uses all check dates, including unknown entries."""

from datetime import UTC, datetime, timedelta


def group_freshness(schedules, now=None):
    now = now or datetime.now(UTC)
    dates = {
        f"{item['section']}/{item['group_id']}": item.get("source_checked_at")
        for item in schedules
    }
    valid = []
    fresh = 0
    for value in dates.values():
        try:
            stamp = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
            age = now - stamp
            if age < timedelta(0):
                continue
            valid.append(stamp)
            fresh += age <= timedelta(hours=24)
        except (ValueError, TypeError):
            pass
    total = len(dates)
    return {
        "group_check_dates": dates,
        "groups_checked_24h": fresh,
        "groups_checked_24h_ratio": fresh / total if total else 0,
        "group_freshness_calculated_at": now.isoformat(),
        "group_checked_at_p10": sorted(valid)[max(0, len(valid) // 10 - 1)].isoformat()
        if valid
        else None,
    }
