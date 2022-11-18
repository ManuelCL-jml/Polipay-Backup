from django.urls import path, include


urlpatterns = [
    path('web/', include("apps.solicitudes.api.web.urls"))
]
