from django.urls import path,include

urlpatterns = [
    path('movil/',include("apps.notifications.api.movil.urls")),
    #path('web/',include("apps.notifications.api.web.urls")),
]