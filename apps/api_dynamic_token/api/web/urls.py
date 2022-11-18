from django.urls import path

from apps.api_dynamic_token.api.web.views.views_dynamic_token import GenerateDynamicToken

urlpatterns = [
    path('v3/GenDynTok/get/', GenerateDynamicToken.as_view())
]
