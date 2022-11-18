from rest_framework import routers
from .views import *
from django.urls import path, include

router = routers.SimpleRouter()
router.register(r'v1/codeefectiva/crud', CRUDCodeEfectiva, basename="endpointCRUDCodeEfectiva")
router.register(r'v1/trantype/crud', CRUDTranType, basename="endpointCRUDTranType")
router.register(r'v1/transmitterhavetrantypes/crud', CRUDTransmitterHaveTranType, basename="endpointCRUDTransmitterHaveTranType")
router.register(r'v1/redefectiva/test', TestConnectionAPISOAP, basename="endpointTestConnectionAPISOAP")
router.register(r'v1/concilationfile/demon', DemonConcilationFile, basename="endpointDemonConcilationFile")
urlpatterns = [
    path('mobile/', include("apps.services_pay.api.mobile.urls")),
] + router.urls

