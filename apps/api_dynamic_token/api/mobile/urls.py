from django.urls import path

# from apps.api_dynamic_token.api.mobile.views.views_token import CreateTokenJWT, GetTokenJWT
from apps.api_dynamic_token.api.mobile.views.views_login_user import EndpointLoginUser, EndpointLogoutUser, \
    DeleteAllOldToken
from apps.api_dynamic_token.api.mobile.views.views_token import TokenConfiguration, GetDynamicToken

urlpatterns = [
    path('v3/TokCon/update/', TokenConfiguration.as_view()),
    path('v3/LogIn/create/', EndpointLoginUser.as_view()),
    path('v3/LogOut/update/', EndpointLogoutUser.as_view()),
    path('v3/GetDynTok/get/', GetDynamicToken.as_view()),
    path('v3/DelAllTok/delete/', DeleteAllOldToken.as_view()),
]
