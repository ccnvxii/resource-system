from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),

    # Додаємо сюди, щоб було прямо за префіксом api/
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('', lambda request: redirect('api/', permanent=False)),
]