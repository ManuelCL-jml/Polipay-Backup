from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/',include("apps.users.urls")),
    path('permission/',include("apps.permision.urls")),
    path('contacts/',include("apps.contacts.urls")),
    path('transaction/',include("apps.transaction.urls")),
    path('report/', include('apps.reportes.urls')),
    path('solicitudes/', include('apps.solicitudes.urls')),
    path('keys/', include('apps.api_dynamic_token.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('api_client/', include('apps.api_client.urls')),
    path('api_stp/', include('apps.api_stp.urls')),
    path('services_pay/', include('apps.services_pay.urls')),
    path('comissions/', include('apps.commissions.urls')),
    path('paycash/', include('apps.paycash.urls')),
]
