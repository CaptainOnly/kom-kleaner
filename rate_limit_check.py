import datetime

# Small margin (seconds) added to any wait so callers resume just after the
# relevant window has actually reset.
_BUFFER = 1


def rate_limit_check(limit, usage, now=None):
    """Return (seconds_to_wait, message) if a Strava rate limit is exceeded.

    ``limit`` and ``usage`` are the comma-separated "15min,daily" strings from
    Strava's X-RateLimit-Limit / X-RateLimit-Usage headers.  When no limit is
    hit ``(None, None)`` is returned.
    """
    if now is None:
        now = datetime.datetime.now(datetime.UTC)

    short_limit, daily_limit = (int(v) for v in limit.split(","))
    short_usage, daily_usage = (int(v) for v in usage.split(","))

    if daily_usage >= daily_limit:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reset = midnight + datetime.timedelta(days=1)
        return (reset - now).total_seconds() + _BUFFER, "Daily rate limit hit"

    if short_usage >= short_limit:
        minute = (now.minute // 15 + 1) * 15
        reset = now.replace(second=0, microsecond=0) + datetime.timedelta(
            minutes=minute - now.minute
        )
        return (reset - now).total_seconds() + _BUFFER, "15 minute rate limit hit"

    return None, None
