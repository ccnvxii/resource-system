# backend/app/views.py
import math
import time
import requests
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .services import NovaPoshtaService
from .models import (
    Resource, Warehouse, Stock, UserRequest,
    DistributionPlan, DistributionItem, Category,
    Unit, RequestPurpose, UserProfile
)
from .serializers import *
from .optimizer.distribute import calculate_distribution, calculate_strict_priority


# --- КАСТОМНА АВТОРИЗАЦІЯ З ПЕРЕВІРКОЮ ПІДТВЕРДЖЕННЯ АДМІНІСТРАТОРОМ ---

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if not user.is_staff:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'is_approved': False}
            )

            if not profile.is_approved:
                # Передаємо і текст, і унікальний код помилки
                raise AuthenticationFailed({
                    "detail": "Ваш обліковий запис ще не підтверджено адміністратором.",
                    "code": "not_approved"
                })

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# --- VIEWSETS ДЛЯ ДОВІДНИКІВ ---

class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RequestPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequestPurpose.objects.all()
    serializer_class = RequestPurposeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- КЛАСИ АВТОРИЗАЦІЇ ТА КОРИСТУВАЧІВ ---

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {'message': 'Реєстрація успішна. Очікуйте підтвердження адміністратора.', 'user_id': user.id},
                status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# --- КЕРУВАННЯ РЕСУРСАМИ ТА СКЛАДАМИ ---

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


# --- ОПЕРАЦІЙНА ЛОГІКА ---

class UserRequestViewSet(viewsets.ModelViewSet):
    queryset = UserRequest.objects.all()
    serializer_class = UserRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = UserRequest.objects.select_related('user', 'resource__unit', 'purpose')
        # Звичайний користувач бачить і змінює лише власні заявки; адміністратор — усі
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def perform_update(self, serializer):
        # Не-адміністратор не може «передати» заявку іншому користувачеві
        if self.request.user.is_staff:
            serializer.save()
        else:
            serializer.save(user=serializer.instance.user)

    def list(self, request, *args, **kwargs):
        from .priority_refresh import refresh_stale_priorities
        refresh_stale_priorities()  # не частіше разу на добу
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or instance.user_id == self.request.user.id):
            raise PermissionDenied("Недостатньо прав для видалення заявки")
        instance.delete()

    def perform_create(self, serializer):
        warehouse_ref = self.request.data.get('warehouse_ref')
        auto_extend_val = self.request.data.get('auto_extend', True)

        lat, lon = None, None
        if warehouse_ref and warehouse_ref != 'ADDRESS_DELIVERY':
            np_service = NovaPoshtaService(api_key=settings.NOVA_POSHTA_API_KEY)
            lat, lon = np_service.get_warehouse_coordinates(warehouse_ref)
        else:
            try:
                lat = float(self.request.data.get('latitude')) if self.request.data.get('latitude') else None
                lon = float(self.request.data.get('longitude')) if self.request.data.get('longitude') else None
            except (ValueError, TypeError):
                lat, lon = None, None

        save_kwargs = {
            'latitude': lat,
            'longitude': lon,
            'auto_extend': auto_extend_val
        }

        if self.request.data.get('due_date'):
            save_kwargs['due_date'] = self.request.data.get('due_date')

        if not self.request.user.is_staff:
            save_kwargs['user'] = self.request.user
            serializer.save(**save_kwargs)
        else:
            user_id = self.request.data.get("user")
            if user_id and str(user_id) != str(self.request.user.id):
                target = User.objects.filter(id=user_id).select_related("profile").first()
                profile = getattr(target, "profile", None) if target else None
                if target and not target.is_staff and not (profile and profile.is_approved):
                    raise PermissionDenied("Користувач ще не підтверджений адміністратором")
            save_kwargs["user_id"] = user_id if user_id else self.request.user.id
            serializer.save(**save_kwargs)


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action == "destroy":
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=["patch"])
    def update_amount(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Доступ заборонено"}, status=status.HTTP_403_FORBIDDEN)
        stock = self.get_object()
        try:
            stock.amount = int(request.data.get('amount'))
            stock.save()
            return Response({"status": "success", "new_amount": stock.amount})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def add_resource(self, request):
        if not request.user.is_staff:
            return Response({"error": "Тільки адміністратор може поповнювати склад"}, status=403)

        warehouse_id = request.data.get('warehouse')
        resource_id = request.data.get('resource')
        amount_to_add = request.data.get('amount')

        if not all([warehouse_id, resource_id, amount_to_add]):
            return Response({"error": "Неповні дані для поповнення"}, status=400)

        try:
            with transaction.atomic():
                amount_int = int(amount_to_add)
                stock, created = Stock.objects.get_or_create(
                    warehouse_id=warehouse_id,
                    resource_id=resource_id,
                    defaults={'amount': 0}
                )
                stock.amount += amount_int
                stock.save()

                return Response({
                    "status": "success",
                    "message": f"Додано {amount_int} до складу {stock.warehouse.name}"
                })
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# --- API ДЛЯ АЛГОРИТМУ ОПТИМІЗАЦІЇ ---

class DistributeResourcesView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            from .priority_refresh import refresh_stale_priorities
            refresh_stale_priorities()  # не частіше разу на добу
            with transaction.atomic():
                today = timezone.now().date()

                expired_requests = UserRequest.objects.filter(
                    status__in=['new', 'partial'],
                    due_date__lt=today
                )

                expired_requests.filter(auto_extend=False).update(status='expired')

                for req in expired_requests.filter(auto_extend=True):
                    req.due_date = today + timedelta(days=5)
                    req.extension_count += 1
                    req.save()

                active_requests_qs = UserRequest.objects.exclude(
                    status__in=['done', 'expired']
                ).select_related('resource').select_for_update(skip_locked=True)

                stocks_qs = Stock.objects.filter(amount__gt=0).select_related('warehouse').select_for_update(
                    skip_locked=True)

                requests_data = []
                for r in active_requests_qs:
                    needed = int(r.quantity_requested - r.quantity_allocated)
                    if needed > 0:
                        raw_p = float(r.priority) if r.priority is not None else 0.5
                        # Алгоритми оптимізації очікують 10-бальну шкалу [0.0 - 10.0]
                        priority_10 = round(raw_p * 10.0, 2) if raw_p <= 1.0 else round(raw_p, 2)
                        requests_data.append({
                            'id': r.id,
                            'resource_id': r.resource_id,
                            'is_strategic': r.resource.is_strategic,
                            'amount_needed': needed,
                            'priority': priority_10,
                            'lat': float(r.latitude) if r.latitude else None,
                            'lng': float(r.longitude) if r.longitude else None
                        })

                stocks_data = []
                for s in stocks_qs:
                    stocks_data.append({
                        'warehouse_id': s.warehouse_id,
                        'resource_id': s.resource_id,
                        'amount': int(s.amount),
                        'lat': float(s.warehouse.latitude) if s.warehouse.latitude else None,
                        'lng': float(s.warehouse.longitude) if s.warehouse.longitude else None
                    })

                strategy = request.data.get('strategy', 'hybrid')

                if strategy == 'hybrid':
                    triage_reqs = [r for r in requests_data if r.get('is_strategic')]
                    fairness_reqs = [r for r in requests_data if not r.get('is_strategic')]

                    plan_triage = calculate_strict_priority(triage_reqs, stocks_data) if triage_reqs else []
                    plan_fairness = calculate_distribution(fairness_reqs, stocks_data) if fairness_reqs else []

                    plan_items_data = plan_triage + plan_fairness

                elif strategy == 'triage':
                    plan_items_data = calculate_strict_priority(requests_data, stocks_data)

                else:
                    plan_items_data = calculate_distribution(requests_data, stocks_data)

                if not plan_items_data:
                    return Response({"message": "Немає доступних комбінацій для розподілу ресурсів"}, status=200)

                new_plan = DistributionPlan.objects.create()

                req_map = {req.id: req for req in active_requests_qs}
                stock_map = {(s.warehouse_id, s.resource_id): s for s in stocks_qs}

                items_to_create = []
                requests_to_update = set()
                stocks_to_update = set()

                for item in plan_items_data:
                    amount_int = int(item['amount'])
                    if amount_int <= 0:
                        continue

                    req = req_map.get(item['request_id'])
                    if not req:
                        continue

                    stock = stock_map.get((item['warehouse_id'], req.resource_id))
                    if not stock:
                        continue

                    items_to_create.append(
                        DistributionItem(
                            plan=new_plan,
                            request=req,
                            warehouse_id=item['warehouse_id'],
                            amount=amount_int
                        )
                    )

                    req.quantity_allocated += amount_int
                    req.status = 'done' if req.quantity_allocated >= req.quantity_requested else 'partial'
                    requests_to_update.add(req)

                    stock.amount -= amount_int
                    stocks_to_update.add(stock)

                DistributionItem.objects.bulk_create(items_to_create)

                if requests_to_update:
                    UserRequest.objects.bulk_update(list(requests_to_update),
                                                    ['quantity_allocated', 'status', 'due_date', 'extension_count'])

                if stocks_to_update:
                    Stock.objects.bulk_update(list(stocks_to_update), ['amount'])

                return Response(DistributionPlanSerializer(new_plan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Критична помилка розрахунку: {e}")
            return Response({"error": "База даних тимчасово зайнята. Спробуйте ще раз."}, status=status.HTTP_423_LOCKED)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DistributionItem.objects.select_related(
        'request__user', 'request__resource', 'warehouse', 'plan'
    ).all().order_by('-plan__created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]


# --- NOVA POSHTA PROXY ---

class NovaPoshtaProxyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        np = NovaPoshtaService(settings.NOVA_POSHTA_API_KEY)
        action = request.data.get("action")

        if action == "get_cities":
            res = np.get_cities(request.data.get("search", ""))
            settlements = (res.get("data", []) and res["data"][0].get("Addresses", [])) or []
            # Debug: виводимо перший результат щоб бачити поля
            if settlements:
                print(f"[NP Cities] Sample keys: {list(settlements[0].keys())}")
            return Response(settlements)

        if action == "get_warehouses":
            res = np.get_warehouses(request.data.get("city_ref"))
            return Response(res.get("data", []))

        if action == "get_streets":
            city_ref = request.data.get("city_ref")
            search = request.data.get("search", "").strip()

            res = np.get_streets(city_ref, search)
            raw_data = res.get("data", [])

            streets_list = []
            if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
                first = raw_data[0]
                if isinstance(first, dict):
                    if "Addresses" in first and isinstance(first["Addresses"], list):
                        streets_list = first["Addresses"]
                    elif "AddressesList" in first and isinstance(first["AddressesList"], list):
                        streets_list = first["AddressesList"]
                    elif "Streets" in first and isinstance(first["Streets"], list):
                        streets_list = first["Streets"]
                    elif "Description" in first:
                        streets_list = raw_data
                else:
                    streets_list = raw_data

            final_streets = []
            for s in streets_list:
                if isinstance(s, dict):
                    desc = (s.get("Present")
                            or s.get("SettlementStreetDescription")
                            or s.get("Description")
                            or s.get("StreetDescription"))
                    if desc:
                        st_type = s.get("StreetsType")
                        if st_type and not desc.startswith(st_type) and not s.get("Present"):
                            desc = f"{st_type} {desc}"
                        s["Description"] = desc
                        s["Presentation"] = desc
                        final_streets.append(s)

            return Response(final_streets)

        return Response({"error": "Invalid action"}, status=400)

# --- ВІДНОВЛЕННЯ ПАРОЛЯ ЗА КОДОМ З ЕЛЕКТРОННОЇ ПОШТИ ---

PASSWORD_RESET_TTL = 10 * 60        # код дійсний 10 хвилин
PASSWORD_RESET_COOLDOWN = 60        # повторне надсилання не частіше, ніж раз на хвилину
PASSWORD_RESET_MAX_ATTEMPTS = 5     # спроб введення коду


def _reset_cache_key(email):
    return f"pwreset:{email.strip().lower()}"


class PasswordResetRequestView(APIView):
    """Крок 1: надсилає 6-значний код на пошту, вказану при реєстрації."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.core.cache import cache
        from django.core.mail import send_mail
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        import secrets
        from django.contrib.auth.hashers import make_password

        email = (request.data.get('email') or '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Введіть коректну електронну пошту, яку вказували при реєстрації."}, status=400)

        key = _reset_cache_key(email)
        existing = cache.get(key)
        now = time.time()
        if existing and now - existing['sent_at'] < PASSWORD_RESET_COOLDOWN:
            wait = int(PASSWORD_RESET_COOLDOWN - (now - existing['sent_at']))
            return Response({"error": f"Код уже надіслано. Повторити можна через {wait} с."}, status=429)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            code = f"{secrets.randbelow(1_000_000):06d}"
            cache.set(key, {
                'hash': make_password(code),
                'attempts': 0,
                'sent_at': now,
                'user_id': user.id,
            }, PASSWORD_RESET_TTL)
            try:
                send_mail(
                    subject="ResQ System — код для скидання пароля",
                    message=(
                        f"Ваш код для скидання пароля: {code}\n\n"
                        f"Код дійсний {PASSWORD_RESET_TTL // 60} хвилин. "
                        f"Якщо ви не запитували скидання — просто проігноруйте цей лист."
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Не вдалося надіслати лист зі скиданням пароля")
                cache.delete(key)
                return Response(
                    {"error": "Не вдалося надіслати лист. Пошту на сервері не налаштовано або вона недоступна — зверніться до адміністратора."},
                    status=503,
                )

        # Однакова відповідь незалежно від того, чи існує акаунт (щоб не розкривати зареєстровані адреси)
        return Response({"message": "Якщо акаунт із такою поштою існує, ми надіслали на неї код підтвердження."})


class PasswordResetConfirmView(APIView):
    """Крок 2: перевіряє код і встановлює новий пароль."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.core.cache import cache
        from django.contrib.auth.hashers import check_password
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        email = (request.data.get('email') or '').strip().lower()
        code = str(request.data.get('code') or '').strip()
        new_password = request.data.get('new_password') or ''

        key = _reset_cache_key(email)
        entry = cache.get(key)
        if not entry:
            return Response({"error": "Код недійсний або термін його дії минув. Запросіть новий."}, status=400)

        if entry['attempts'] >= PASSWORD_RESET_MAX_ATTEMPTS:
            cache.delete(key)
            return Response({"error": "Забагато невдалих спроб. Запросіть новий код."}, status=400)

        if not check_password(code, entry['hash']):
            entry['attempts'] += 1
            remaining = max(0, PASSWORD_RESET_TTL - int(time.time() - entry['sent_at']))
            cache.set(key, entry, remaining or 1)
            return Response({"error": "Невірний код."}, status=400)

        user = User.objects.filter(id=entry['user_id'], is_active=True).first()
        if not user:
            cache.delete(key)
            return Response({"error": "Акаунт не знайдено."}, status=400)

        if len(new_password) < 8:
            return Response({"error": "Пароль має містити щонайменше 8 символів."}, status=400)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": " ".join(e.messages)}, status=400)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        cache.delete(key)
        return Response({"message": "Пароль успішно змінено. Тепер ви можете увійти."})


class PasswordResetVerifyView(APIView):
    """Крок 2: лише перевіряє код (не змінює пароль і не «спалює» код)."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.core.cache import cache
        from django.contrib.auth.hashers import check_password

        email = (request.data.get('email') or '').strip().lower()
        code = str(request.data.get('code') or '').strip()

        key = _reset_cache_key(email)
        entry = cache.get(key)
        if not entry:
            return Response({"error": "Код недійсний або термін його дії минув. Запросіть новий."}, status=400)

        if entry['attempts'] >= PASSWORD_RESET_MAX_ATTEMPTS:
            cache.delete(key)
            return Response({"error": "Забагато невдалих спроб. Запросіть новий код."}, status=400)

        if not check_password(code, entry['hash']):
            entry['attempts'] += 1
            remaining = max(0, PASSWORD_RESET_TTL - int(time.time() - entry['sent_at']))
            cache.set(key, entry, remaining or 1)
            left = PASSWORD_RESET_MAX_ATTEMPTS - entry['attempts']
            return Response({"error": f"Невірний код. Залишилось спроб: {left}."}, status=400)

        return Response({"valid": True})


class PublicStatsView(APIView):
    """Публічна статистика для лендингу (доступна без авторизації; лише агреговані числа)."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "stocks": Stock.objects.filter(amount__gt=0).count(),
            "requests": UserRequest.objects.exclude(status='done').count(),
            "warehouses": Warehouse.objects.count(),
        })
