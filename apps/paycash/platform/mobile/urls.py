from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.paycash.platform.mobile.views.views import TokenPayCash, CreateReferencePayCash, CancelReferencePayCash, \
    ListReferencePayCash, DetailReferencePayCash
from apps.paycash.platform.mobile.views.views_notification_paycash import PayCashNotifica

router = DefaultRouter()
router.register(r'v1/CreRefPayCas/create', CreateReferencePayCash, basename='create-reference')
router.register(r'v1/PayCasNot/create', PayCashNotifica, basename='paycash-notifica')


urlpatterns = [
    path("v1/TokPay/get/", TokenPayCash.as_view()),
    path("v1/CanRef/get/", CancelReferencePayCash.as_view()),
    path("v1/LisRef/list/", ListReferencePayCash.as_view()),
    path("v1/DetRef/list/", DetailReferencePayCash.as_view()),
] + router.urls
