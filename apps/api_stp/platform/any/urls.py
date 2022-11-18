from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.api_stp.platform.any.views.views_stp import DetailPendingTransaction
from apps.api_stp.platform.any.views.views_cobranza_stp import CobranzaAbonoSTP

router = DefaultRouter()
router.register(r'v1/CobranzaAbono/create', CobranzaAbonoSTP, basename='cobranza_abono')

urlpatterns = [
    path('v1/StatusChange/update/', DetailPendingTransaction.as_view()),
] + router.urls
