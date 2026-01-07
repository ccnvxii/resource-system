from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect  # <-- Додайте цей імпорт

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),

    # Додайте цей рядок:
    path('', lambda request: redirect('api/resources/', permanent=False)),
]