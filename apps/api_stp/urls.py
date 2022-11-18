from django.urls import path, include

urlpatterns = [
    path('any/', include('apps.api_stp.platform.any.urls')),
]
