from django.urls import path, include

from apps.users.views import CheckCodeUserGenericAPIView, CheckCodeUserAppToken

urlpatterns = [
    path('web/', include("apps.users.api.web.urls")),
    path('movil/', include("apps.users.api.movil.urls")),
    path('web/admin/', include("apps.users.api.web.admin.urls")),
    path('web/cliente/', include("apps.users.api.web.cliente.urls")),
    path('v2/check/code/', CheckCodeUserGenericAPIView.as_view()),
    path('v3/check/code/', CheckCodeUserAppToken.as_view()),
]
