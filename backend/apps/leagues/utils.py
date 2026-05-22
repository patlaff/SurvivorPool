from django.utils import timezone


def is_draft_open(league) -> bool:
    """
    Determine whether the draft is currently open for the given league.

    Resolution order (first match wins):
    1. draft_force_open == True  → open
    2. draft_close_at set and now >= draft_close_at  → closed
    3. draft_close_at set and now <  draft_close_at  → open
    4. season.draft_lock_date set and today >= lock_date  → closed
    5. Everything else  → open
    """
    if getattr(league, 'is_test', False):
        return True
    if league.draft_force_open:
        return True
    if league.draft_close_at is not None:
        return timezone.now() < league.draft_close_at
    lock_date = league.season.draft_lock_date
    if lock_date is None:
        return True
    return timezone.now().date() < lock_date
