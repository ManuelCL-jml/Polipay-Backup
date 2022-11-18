from django.urls import path, include

from apps.users.views import CheckCodeUserGenericAPIView, CheckCodeUserAppToken

urlpatterns = [
    path('web/', include("apps.commissions.api.web.urls")),
]
