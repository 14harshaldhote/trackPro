from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Authentication URLs
    path('api/', include('api.urls')),
    path('', include('core.urls')),
]
