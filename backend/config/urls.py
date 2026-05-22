from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.castaways.urls')),
    path('api/v1/', include('apps.leagues.urls')),
    path('api/v1/', include('apps.admin_panel.urls')),
]
