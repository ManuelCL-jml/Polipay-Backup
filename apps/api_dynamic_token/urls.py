from django.urls import path, include

urlpatterns = [
	path('web/', include("apps.api_dynamic_token.api.web.urls")),
	path('mobile/', include("apps.api_dynamic_token.api.mobile.urls")),
]
