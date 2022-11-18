from django.urls import path
from rest_framework import routers
from apps.users.api.web.cliente.views.views_centro_costo import *
from apps.users.api.web.cliente.views.views_cliente_externo import CreateClienteExternoFisico, \
    ListExternsClients, UpdateClienteExternoFisico, DeleteClienteExternoFisico, ViewDetailsExternClient,\
    clienteListFilter_C_E
from apps.users.api.web.cliente.views.views_colaborador import *
from apps.users.api.web.cliente.views.views_grupo_persona import *

routers = routers.SimpleRouter()

routers.register(r'v2/CosCen/create', CreateCostCenter, basename='create-centro-costo')
routers.register(r'v2/centro-costos/detail', GetCentroCostos, basename='centro-costos')
routers.register(r'v2/GruPerExt/create', GrupoPersonalExterno, basename='grupo-personal-externo')
routers.register(r'v2/Colaborador/cu', Colaborador, basename='crear-editar-colaborador')
routers.register(r'v2/ColDocSub/cu', CargarDocumentos, basename='crear-editar-documentos-colaborador')
routers.register(r'v2/ColDocBaj/create', DesactivarColaborador, basename='Dar-de-baja-colaborador-por-documento')
routers.register(r'v3/Col/list', VerColaborador, basename='listar-colaborador')
routers.register(r'v3/CCostos/upd', updateCentroCostos, basename='actualizacion-CCostos')
routers.register(r'v3/CCostos/soldis', SolDismissCC, basename='sol-baja-CCostos')
routers.register(r'v3/ExtFisCli/list', ListExternsClients, basename='clienteListFilter_C_E')
routers.register(r'v3/ExtFisCli/create', CreateClienteExternoFisico, basename='crea_CE_fisico')
routers.register(r'v3/ExtFisCli/update', UpdateClienteExternoFisico, basename='actualiza_CE_fisico')
routers.register(r'v3/ExtFisCli/delete', DeleteClienteExternoFisico, basename='elimina_CE_fisico')
routers.register(r'v3/ExtFisCli/get', ViewDetailsExternClient, basename='elimina_CE_fisico')
routers.register(r'v3/EditDomFiscalReq/create', SolicitudEditarDomicilioFiscal, basename='solicitud_editar_dom_fiscal')
routers.register(r'v3/EditClaTraReq/create', SolicitudEditarClaveTraspasoFinal, basename='solicitud_editar_clave_traspaso')
routers.register(r'v3/AmdClaTra/upd', AmendClaveTraspasoFinal, basename='solicitud_editar_clave_traspaso')
routers.register(r'v3/AmdDomFis/upd', AmendDomicilioFiscal, basename='solicitud_editar_clave_traspaso')
routers.register(r'v3/SolAltRepLeg/create', AltaRepresentanteLegal, basename='solicitud_editar_clave_traspaso')
routers.register(r'v3/clienteListFilter_C_E/list', clienteListFilter_C_E,
                 basename='clienteListFilter_C_E')

urlpatterns = [
    path('v2/centro-costos/list/', ListarCentroCosto.as_view(), name='listar-centro'),
    path('v2/SeaPerExt/list/', SearchPersonalExterno.as_view(), name='buscar-personal'),
    path('v2/LisGruPer/list/', ListGrupoPersona.as_view(), name='buscar-personal'),
    path('v2/DelGruPer/delete/', DeleteGrupoPersona.as_view(), name='delete-grupo'),
    path('v2/DetGruPer/list/', DetailGrupoPersona.as_view(), name='delete-grupo-persona'),
    path('v2/EdiGruPer/update/', EditGrupoPersona.as_view(), name='delete-grupo-persona'),
    path('v2/CentroCostos/list/', CentroCostos.as_view(), name='listarCentroCostos'),
    path('v2/ColDet/get/', ColaboratorsDetails.as_view(), name='detalle-colaborador'),
    path('v2/CarResDes/', CartaResponsiva),
    path('v1/LisCosCenFil/list/', ListCostCenterFilter.as_view()),
    path('v3/LisCosCenCueEje/list/', GetCostCenter.as_view()),


    # """ CENTRO COSTOS """
    path('v3/CorApeCosCen/update/', CorregirAperturaCostCenter.as_view()),
    path('v3/DelCosCen/delete/', DeleteCostCenter.as_view()),
    path('v3/DelRepLeg/delete/', DeleteRepresentanteLegal.as_view()),
    path('v3/LisCosCenActCli/list/', ListCostCenterActiveClient.as_view()),
    path('v3/LisSolCosCenCli/list/', ListSolicitudesCostCenterClient.as_view()),
    path('v3/CorRepLeg/gu/', CorregirNuevoRepresentanteLegal.as_view()),

    # """ COLABORADORES """
    path('v3/SolDevAltCol/gu/', SolicitudDevueltaAltaColaborador.as_view()),
    path('v3/EdiCol/gu/', EditarColaborador.as_view()),
    path('v3/SolEdiCol/gu/', SolicitudDevueltaEditarColaborador.as_view()),
    path('v3/LisColCli/list/', ListColaboradoresClient.as_view()),
    path('v3/LisSolColCli/list/', ListSolicitudesColaboradoresCliente.as_view()),
    path('v3/LisColAct/list/', ListColaboradoresActivosCliente.as_view()),
] + routers.urls

