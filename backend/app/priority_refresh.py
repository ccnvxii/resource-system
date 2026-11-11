"""
Ліниве щодобове оновлення пріоритетів заявок.

Пріоритет залежить від дедлайну лише через часовий множник (див. utils.calculate_time_multiplier):
далі ніж за TIME_WINDOW_DAYS днів множник стале (0.5), тож такі заявки перераховувати не треба.
Тому щодоби перераховуємо лише заявки з близьким або простроченим дедлайном, одним bulk_update.

Планувальник (cron/Celery) не потрібен: оновлення виконується при першому зверненні за календарну добу
(формування розподілу, перегляд списку заявок) і більше не повторюється, доки не настане нова доба.
"""
from datetime import timedelta

from django.utils import timezone

from .utils import calculate_request_priority

TIME_WINDOW_DAYS = 10   # 1.0 - days_left * 0.05 досягає нижньої межі 0.5 при days_left >= 10
BATCH_SIZE = 500

_last_refresh_date = None


def refresh_stale_priorities(force=False):
    """Повертає кількість заявок, у яких змінився пріоритет."""
    global _last_refresh_date
    from .models import UserRequest

    today = timezone.now().date()
    if not force and _last_refresh_date == today:
        return 0

    qs = (
        UserRequest.objects
        .filter(status__in=['new', 'partial'], due_date__lte=today + timedelta(days=TIME_WINDOW_DAYS))
        .select_related('purpose', 'resource__category')
    )

    changed = []
    for req in qs.iterator(chunk_size=BATCH_SIZE):
        new_priority = calculate_request_priority(
            purpose_weight=req.purpose.weight,
            category_criticality=req.resource.category.criticality if req.resource.category else 0.5,
            latitude=req.latitude,
            longitude=req.longitude,
            due_date=req.due_date,
            extension_count=req.extension_count,
        )
        if req.priority is None or abs(req.priority - new_priority) > 1e-9:
            req.priority = new_priority
            changed.append(req)

    if changed:
        UserRequest.objects.bulk_update(changed, ['priority'], batch_size=BATCH_SIZE)

    _last_refresh_date = today
    return len(changed)
