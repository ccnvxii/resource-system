import math
import datetime
import numpy as np
from django.utils import timezone
from .services import GeoFrontService


def calculate_front_multiplier(user_lat, user_lon):
    """
    СППР-модель динамічної гео-пріоритезації
    """
    if user_lat is None or user_lon is None:
        return 0.15  # Дефолтний мінімальний пріоритет для невідомих локацій

    geo_service = GeoFrontService()
    front_points = geo_service.get_front_line_points()

    if not front_points:
        return 0.15

    try:
        u_lat = float(user_lat)
        u_lon = float(user_lon)

        # --- ВЕКТОРНИЙ РОЗРАХУНОК ГАВЕРСИНУСА (NUMPY) ---
        front_coords = np.array(front_points, dtype=float)

        u_lat_rad, u_lon_rad = np.radians(u_lat), np.radians(u_lon)
        front_lat_rad = np.radians(front_coords[:, 0])
        front_lon_rad = np.radians(front_coords[:, 1])

        dlat = front_lat_rad - u_lat_rad
        dlon = front_lon_rad - u_lon_rad

        a = np.sin(dlat / 2.0) ** 2 + np.cos(u_lat_rad) * np.cos(front_lat_rad) * np.sin(dlon / 2.0) ** 2
        c = 2.0 * np.arcsin(np.sqrt(a))

        R = 6371.0 # Радіус Землі в км
        distances_km = R * c
        min_dist = np.min(distances_km)

        # --- НОРМАЛІЗОВАНА ЗОНАЛЬНА МОДЕЛЬ (0 - 1.0) ---
        if min_dist <= 100.0:
            # 1. Зона бойових дій
            return math.exp(-min_dist / 120.0)
        elif min_dist <= 220.0:
            # 2. Прифронтова зона
            return 0.45
        else:
            # 3. Стратегічний тил
            distance_from_front_zone = min_dist - 220.0
            penalty = 0.33 * math.exp(-distance_from_front_zone / 150.0)
            return max(0.15, penalty)

    except (ValueError, TypeError) as e:
        print(f"Помилка гео-модуля: {e}")
        return 0.15


def calculate_time_multiplier(due_date):
    """
    СППР-модель пріоритезації за часовим лімітом (Time-Limit Degradation Model).
    Повертає нормалізований коефіцієнт в інтервалі [0.5; 1.0].
    """
    if not due_date:
        return 0.5

    try:
        today = timezone.now().date()

        if isinstance(due_date, str):
            due_date = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()

        days_left = (due_date - today).days

        if days_left <= 0:
            return 1.0

        # Лінійне падіння: -0.05 за кожен день відстрочки
        multiplier = 1.0 - (days_left * 0.05)

        return max(0.5, min(1.0, multiplier))

    except Exception as e:
        print(f"Помилка часового модуля: {e}")
        return 0.5


def calculate_request_priority(purpose_weight, category_criticality, latitude, longitude, due_date, extension_count):
    # Якщо purpose_weight передається за 10-бальною шкалою (наприклад, 6.0, 9.0), нормалізуємо до [0; 1]
    k_purp = float(purpose_weight) / 10.0 if float(purpose_weight) > 1.0 else float(purpose_weight)
    k_crit = float(category_criticality) if category_criticality else 0.5

    k_geo = calculate_front_multiplier(latitude, longitude)
    k_time = calculate_time_multiplier(due_date)

    # Штраф тепер адаптований під шкалу [0; 1] (наприклад, -0.01 за кожен цикл, максимум -0.05)
    age_penalty = (extension_count * 0.01) if extension_count <= 5 else 0.05
    alpha, beta, gamma, delta = 0.35, 0.25, 0.25, 0.15

    weighted_sum = (alpha * k_purp) + (beta * k_time) + (gamma * k_geo) + (delta * k_crit)
    final_index = weighted_sum - age_penalty

    # Зберігаємо в базі даних в діапазоні [0.0; 1.0] з округленням до 3 знаків
    return round(max(0.0, min(1.0, final_index)), 3)