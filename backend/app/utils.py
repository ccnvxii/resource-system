import math
from django.conf import settings
from .services import GeoFrontService


def calculate_front_multiplier(user_lat, user_lon):
    """
    Розраховує динамічний множник пріоритету на основі живих даних лінії фронту.
    Використовує експоненційне затухання: чим ближче до фронту, тим вищий пріоритет.

    Винесено в окремий файл утиліт для запобігання циклічного імпорту в Django.
    """
    geo_service = GeoFrontService()
    front_points = geo_service.get_front_line_points()

    if not front_points:
        return 1.0

    try:
        # Перетворюємо координати користувача на float про всяк випадок
        u_lat = float(user_lat)
        u_lon = float(user_lon)

        # Обчислюємо відстань до найближчої точки фронту (в км)
        # Коефіцієнт 111 переводить градуси сітки у кілометри
        distances = [
            math.sqrt((u_lat - float(fx)) ** 2 + (u_lon - float(fy)) ** 2) * 111
            for fx, fy in front_points
        ]

        min_dist = min(distances) if distances else 300

        # Множник пріоритету: максимум 3.0 на самому фронті,
        # плавно затухає до 1.0 на відстані понад 250-300 км
        multiplier = 3.0 * math.exp(-min_dist / 250)
        return max(1.0, multiplier)

    except (ValueError, TypeError) as e:
        print(f"Error inside calculate_front_multiplier logic: {e}")
        return 1.0
