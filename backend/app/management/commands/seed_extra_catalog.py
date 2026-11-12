from django.core.management.base import BaseCommand

from app.seed_extra import seed_extra_catalog


class Command(BaseCommand):
    help = (
        "Додає додаткові довідники (одиниці, категорії, ресурси, склади, типи призначення) "
        "та стартові залишки для НОВИХ позицій. Безпечна для повторного запуску: "
        "нічого не видаляє й не змінює наявні залишки."
    )

    def handle(self, *args, **options):
        created = seed_extra_catalog(force_stock=False)
        self.stdout.write(self.style.SUCCESS(
            "Додано: " + ", ".join(f"{k} - {v}" for k, v in created.items())
        ))
