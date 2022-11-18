from django.urls import path
from rest_framework import routers
from apps.transaction.api.system.views.runCron import *

router = routers.DefaultRouter()
#router.register(r'v2/transferenciaM', transaccionesMasivasExcel, basename='crear excel')

urlpatterns = [
    path('v3/SystemCron/list/', SystemCronRun.as_view()),
] + router.urls
