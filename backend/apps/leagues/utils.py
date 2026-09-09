from django.utils import timezone


def joinable_season():
    """
    The season a newly created league should belong to.

    Normally that is the active season.  Between seasons the active season is
    dormant (finished, archived, no longer accepting leagues), so new leagues are
    prepared for the *next* season instead — its row is created empty and stays
    that way until the survivoR dataset publishes the cast, at which point
    _sync_season() fills it in and activates it.

    Returns None when there is no active season at all.
    """
    from apps.castaways.models import Season

    active = Season.objects.filter(is_active=True, version='US').first()
    if active is None:
        return None
    if active.allows_new_leagues:
        return active

    next_number = active.season_number + 1
    season, _ = Season.objects.get_or_create(
        season_number=next_number,
        defaults={
            'name': f'Survivor Season {next_number}',
            'version': 'US',
            'is_active': False,
        },
    )
    return season


def is_draft_open(league) -> bool:
    """
    Determine whether the draft is currently open for the given league.

    Resolution order (first match wins):
    0. season has no castaways yet  → closed
    1. draft_force_open == True  → open
    2. draft_close_at set and now >= draft_close_at  → closed
    3. draft_close_at set and now <  draft_close_at  → open
    4. season.draft_lock_date set and today >= lock_date  → closed
    5. Everything else  → open
    """
    # A draft cannot open before the season's cast exists — there would be nothing
    # to pick.  This outranks every override, is_test and draft_force_open included.
    if not league.season.has_data:
        return False
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
