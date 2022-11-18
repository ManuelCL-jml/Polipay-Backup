from django.urls import path, include

urlpatterns = [
    path('mobile/', include("apps.paycash.platform.mobile.urls")),
]
