from django.core.management.base import BaseCommand

from app.priority_refresh import refresh_stale_priorities


class Command(BaseCommand):
    help = (
        'Примусовий перерахунок пріоритетів заявок за дедлайном (одним bulk_update). '
        'Зазвичай не потрібен: система робить це автоматично при першому зверненні за добу.'
    )

    def handle(self, *args, **kwargs):
        changed = refresh_stale_priorities(force=True)
        self.stdout.write(self.style.SUCCESS(f'Пріоритети оновлено для {changed} заявок.'))
