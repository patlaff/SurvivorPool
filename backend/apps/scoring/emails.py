import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _admin_url() -> str:
    return getattr(settings, 'ADMIN_SITE_URL', 'http://localhost')


def notify_next_season_detected(current_number: int, next_number: int, castaway_count: int) -> None:
    """Email superadmins when the first castaway data for the next season appears."""
    subject = f'[SurvivorPool] Season {next_number} data has appeared'
    body = (
        f'The survivoR dataset now contains {castaway_count} castaway(s) for Season {next_number}.\n\n'
        f'This is the initial detection — the full cast may not be announced yet.\n'
        f'You will receive another email when the cast looks complete (≥18 castaways).\n\n'
        f'Log in to the admin panel when ready to progress:\n'
        f'{_admin_url()}\n'
    )
    _send(subject, body)


def notify_next_season_complete(current_number: int, next_number: int, castaway_count: int) -> None:
    """Email superadmins when the next season's cast reaches the complete threshold."""
    subject = f'[SurvivorPool] Season {next_number} cast looks complete ({castaway_count} castaways)'
    body = (
        f'The survivoR dataset now has {castaway_count} castaways for Season {next_number}.\n\n'
        f'The cast appears to be complete. Log in to the admin panel and click\n'
        f'"Progress from Season {current_number} to Season {next_number}" to activate the new season.\n\n'
        f'{_admin_url()}\n'
    )
    _send(subject, body)


def _send(subject: str, body: str) -> None:
    recipients = getattr(settings, 'SUPERADMIN_EMAILS', [])
    from_email = getattr(settings, 'EMAIL_HOST_USER', '') or 'noreply@survivorpool'
    if not recipients:
        logger.warning('_send: SUPERADMIN_EMAILS is empty, skipping notification')
        return
    try:
        send_mail(subject, body, from_email, recipients, fail_silently=False)
        logger.info('Sent notification email to %s: %s', recipients, subject)
    except Exception:
        logger.exception('Failed to send notification email: %s', subject)
