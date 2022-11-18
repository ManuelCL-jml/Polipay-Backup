from django.urls import path
from rest_framework import routers
from .views import *

router = routers.SimpleRouter()
router.register(r'v1/APIRequest/create', CreateAPIRequest, basename="endpointCreateAPIRequest")
router.register(r'v1/APIReqList/list', ListAPIRequest, basename="endpointListAPIRequest")
router.register(r'v1/APIStatus/update', ChangeRequestStatus, basename="endpointChangeRequestStatus")
router.register(r'v1/APICredList/list', ListAPICredentials, basename="endpointListAPICredentials")
router.register(r'v1/APIFilterCredList/list', FilterAPICredentials, basename="endpointFilterAPICredentials")
router.register(r'v1/APICECardStock/list', CuentaEjeCardStock, basename="endpointCuentaEjeCardStock")
router.register(r'v1/APIListPEDetails/list', ListPersonalExternoDetails, basename="endpointListPersonalExternoDetails")
router.register(r'v1/APIListMovementHistory/list', ListMovementHistory, basename="endpointListMovementHistory")
router.register(r'v1/APIPersonaExterna/create', CreatePersonaExterna, basename="endpointCreatePersonaExterna")
router.register(r'v1/APIBuscarTarjetaInntec/list', BuscarNumeroTarjetaInntec, basename="endpointBuscarNumeroTarjetaInntec")
router.register(r'v1/APIAsignarTarjetaInntecCE/create', AsignarTarjetaInnteCuentaEje, basename="endpointAsignarTarjetaInnteCuentaEje")
router.register(r'v1/APIDispersionMasiva/create', DispersionMasiva, basename="endpointDispersionMasiva")
router.register(r'v1/APIDispersionIndividual/create', DispersionIndividual, basename="endpointDispersionIndividual")
router.register(r'v1/ScriptDispersionMasivaProgramada/list', DispersionMasivaProgramada, basename="endpointDispersionMasivaProgramada")

urlpatterns = [
                  path("v1/APIBlockCredential/update/", BlockApiCredentials.as_view()),
                  path("v1/ResendAPICredential/update/", ResendCredential.as_view()),
                  path("v1/APIAsignaTarjetaPE/update/", AsignarTarjetaInntecPersonalExterno.as_view())
              ] + router.urls
