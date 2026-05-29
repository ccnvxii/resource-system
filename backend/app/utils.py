import math
import datetime
import numpy as np
from django.utils import timezone
from scipy.spatial.distance import cdist
from .services import GeoFrontService


def calculate_front_multiplier(user_lat, user_lon):
    """
    СППР-модель динамічної гео-пріоритезації (Front-Line Proximity Model).
    Версія з оптимізованим векторним пошуком найближчої точки через SciPy cdist.

    Забезпечує жорстку диференціацію:
    - Зона бойових дій (0-80 км) -> Максимальний буст (до 3.0)
    - Стабілізаційні хаби (80-200 км, Дніпро) -> Помітний пріоритет (1.4)
    - Тил ( > 220 км) -> Суворий деградаційний коефіцієнт (0.4 - 1.0)
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

        # --- ВЕКТОРНИЙ РОЗРАХУНОК ЧЕРЕЗ SCIPY (ОПТИМІЗАЦІЯ CPU) ---
        # Формуємо матрицю для поточної координати користувача (1 рядок, 2 стовпці)
        user_coord = np.array([[u_lat, u_lon]])

        # Перетворюємо масив опорних точок лінії фронту у двовимірну матрицю NumPy
        front_coords = np.array(front_points, dtype=float)

        # cdist обчислює евклідову відстань у градусах між точкою користувача
        # та ВСІМА опорними точками лінії зіткнення на рівні компільованого C-коду
        distances_deg = cdist(user_coord, front_coords, metric='euclidean')

        # Знаходимо мінімальний елемент матриці (найближчу точку кривої) та масштабуємо в кілометри
        min_dist = np.min(distances_deg) * 111.0

        # --- РАДИКАЛЬНА МАТЕМАТИЧНА МОДЕЛЬ ЗОНУВАННЯ ---
        if min_dist <= 80.0:
            # 1. Смуга безпосередньої близькості до фронту (Краматорськ)
            return 3.0 * math.exp(-min_dist / 120.0)

        elif min_dist <= 220.0:
            # 2. Оперативно-тактична прифронтова зона (Дніпро, Запоріжжя)
            return 1.4

        else:
            # 3. Стратегічний тил (Вінниця, Львів)
            distance_from_front_zone = min_dist - 220.0
            penalty = math.exp(-distance_from_front_zone / 150.0)

            # Обмежуємо знизу коефіцієнтом 0.4, щоб пріоритет не занулився зовсім
            return max(0.4, penalty)

    except (ValueError, TypeError) as e:
        print(f"Error inside calculate_front_multiplier logic: {e}")
        return 1.0


def calculate_time_multiplier(due_date):
    """
    СППР-модель пріоритезації за часовим лімітом (Time-Limit Degradation Model).

    Реалізує закон лінійного зростання гостроти дефіциту при наближенні дедлайну.
    Гарантує щоденний приріст коефіцієнта на 0.2 протягом 10-денного вікна.
    """
    if not due_date:
        return 1.0

    try:
        today = timezone.now().date()

        # Конвертація рядка у об'єкт date
        if isinstance(due_date, str):
            due_date = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()

        # Обчислення кількості днів, що залишилися до виконання
        days_left = (due_date - today).days

        # Якщо дедлайн настав сьогодні або вже протермінований — максимальний буст х3.0
        if days_left <= 0:
            return 3.0

        # Лінійне зростання пріоритету
        multiplier = 3.0 - (days_left * 0.2)

        # Фіксація діапазону множника [1.0; 3.0]
        return max(1.0, min(3.0, multiplier))

    except Exception as e:
        print(f"Критична помилка розрахунку часового множника: {e}")
        return 1.0