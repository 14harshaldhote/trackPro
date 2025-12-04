from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/', include('api.urls')),  # Commented out - api app doesn't exist
    path('', include('core.urls')),
    path('accounts/', include('allauth.urls')),  # Authentication URLs
]
