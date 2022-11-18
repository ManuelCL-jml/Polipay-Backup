from django.urls import path, include

urlpatterns = [
    path('movil/', include("apps.transaction.api.movil.urls")),
    path('web/', include("apps.transaction.api.web.urls")),
    path('system/', include("apps.transaction.api.system.urls")),
]
