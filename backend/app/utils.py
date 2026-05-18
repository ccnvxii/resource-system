# backend/app/utils.py
import math
from django.utils import timezone
from .services import GeoFrontService


def calculate_front_multiplier(user_lat, user_lon):
    """
    Розраховує динамічний множник пріоритету на основі живих даних лінії фронту.
    Використовує експоненційне затухання: чим ближче до фронту, тим вищий пріоритет.
    """
    if user_lat is None or user_lon is None:
        return 1.0

    geo_service = GeoFrontService()
    front_points = geo_service.get_front_line_points()

    if not front_points:
        return 1.0

    try:
        u_lat = float(user_lat)
        u_lon = float(user_lon)

        # Коефіцієнт 111 переводить градуси сітки у кілометри
        distances = [
            math.sqrt((u_lat - float(fx)) ** 2 + (u_lon - float(fy)) ** 2) * 111
            for fx, fy in front_points
        ]

        min_dist = min(distances) if distances else 300

        # Максимум x3.0 на самому фронті, плавно згасає до 1.0 на відстані 250-300 км
        multiplier = 3.0 * math.exp(-min_dist / 250)
        return max(1.0, multiplier)

    except (ValueError, TypeError) as e:
        print(f"Error inside calculate_front_multiplier logic: {e}")
        return 1.0


def calculate_time_multiplier(due_date):
    """
    СППР-модель пріоритезації за часовим лімітом (Time-Limit Degradation).
    Гарантує лінійне зростання пріоритету при наближенні дедлайну.
    """
    if not due_date:
        return 1.0

    try:
        from django.utils import timezone
        import datetime

        today = timezone.now().date()

        if isinstance(due_date, str):
            due_date = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()

        days_left = (due_date - today).days

        if days_left <= 0:
            return 3.0

        # Чітка інженерна модель (Максимальний буст x3.0, який зменшується з кожним днем)
        # Якщо лишився 1 день (18.05): 3.0 - (1 * 0.2) = 2.8
        # Якщо лишилося 5 днів (22.05): 3.0 - (5 * 0.2) = 2.0
        # Якщо днів більше 10, множник фіксується на базовому 1.0
        multiplier = 3.0 - (days_left * 0.2)

        return max(1.0, min(3.0, multiplier))

    except Exception as e:
        print(f"Критична помилка розрахунку часу: {e}")
        return 1.0