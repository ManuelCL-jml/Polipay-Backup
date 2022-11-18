from rest_framework import routers

from django.urls import path

from .views.centro_costos_views import *


routers = routers.SimpleRouter()
routers.register(r'v2/list/solicitud', Solicitud, basename='create-list-solicitudes')
routers.register(r'v2/verify-documents', VerificacionDocumentos, basename='create-list-solicitudes')
routers.register(r'v2/alta/centro-costos/detail', RetrieveCentroCostos, basename='alta-centro-costos-detail')
# routers.register(r'v2/documents/cost-center', SolicitudAperturaCentroCostos, basename='centro-de-costos-documentos')
routers.register(r'v2/solicitar-saldos', SolicitarSaldos, basename='baja-centro-costo')
routers.register(r'v2/autorizar-saldos', AutorizarSolicitudSaldos, basename='baja-centro-costo')
routers.register(r'v2/ReqTarCom', SolicitarTarjetasCuentaEje, basename='solicitar-tarjetas-CE')
routers.register(r'v2/ChaStaCar', ChangeStatusToCardRequests, basename='solicitar-tarjetas-CE')
routers.register(r'v2/ReqTarCosCen', RequestCardsCostCenters, basename='solicitar-tarjetas-CC')
routers.register(r'v2/CanCarReq/update', CancelRequestCards, basename='solicitar-tarjetas-CC')
routers.register(r'v2/AssingCards/update', AssignCardsCostCenter, basename='solicitar-tarjetas-CC')


urlpatterns = [
    path('v2/baja/centro-costos/detail/', DetailSolicitudBajaCentroCostos.as_view()),
    path('v2/cuenta-eje/list-solicitudes/', ListSolicitudesCuentaEje.as_view()),
    path('v2/solicitar-tarjetas/list-costoUnit-Tarjetas/', GetCostoUnitariosTarjetas.as_view()),
    path('v3/LisReqCarAllCosCen/list/', ListRequestAllCostCenter.as_view()),
    path('v3/LisReqCarCosCen/list/', ListRequestCostCenter.as_view()),
    path('v3/LisAvaCar/list/', ListAvaliableCards.as_view()),
    path('v2/DetReqCar/get/', RequestsCardDetail.as_view()),
    path('v3/DetReqCards/get/', CardsRequestDetails.as_view()),
    path('v2/StaReq/list/', ListStatusToChangeCardRequest.as_view()),
    path('v3/CarAvaCom/get/', StockCardsInCompany.as_view()),
] + routers.urls
