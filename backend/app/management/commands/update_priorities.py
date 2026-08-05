from django.core.management.base import BaseCommand
from app.models import UserRequest
from django.utils import timezone

class Command(BaseCommand):
    help = 'Нічний перерахунок пріоритетів заявок на основі наближення дедлайну'

    def handle(self, *args, **kwargs):
        self.stdout.write("Початок перерахунку пріоритетів...")

        # лише активні заявки
        active_requests = UserRequest.objects.filter(status__in=['new', 'partial'])

        count = 0
        for req in active_requests:
            req.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Успішно оновлено пріоритети для {count} заявок.'))