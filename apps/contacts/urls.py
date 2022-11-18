from django.urls import path,include

urlpatterns = [
    path('movil/',include("apps.contacts.api.movil.urls")),
    path('web/',include("apps.contacts.api.web.urls")),
    # path('web/',include("users.api.web.urls")),
]


