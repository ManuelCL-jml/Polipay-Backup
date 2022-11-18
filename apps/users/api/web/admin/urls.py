from django.urls import path
from rest_framework import routers
from apps.users.api.web.admin.views.views_colaborator import *
from apps.users.api.web.admin.views.views_cuenta_eje import *
from apps.users.api.web.admin.views.views_admin import *
from apps.users.api.web.admin.views.views_centro_costo import *
from apps.users.api.web.admin.views.views_cliente_externo import *


routers = routers.SimpleRouter()

routers.register(r'v2/cuentaeje', CreateCuentaEjeGeneric, basename='create-cuenta-eje')
# routers.register(r'v2/cuentaeje/detail', RetrieveCuentaEje, basename='cuenta-eje-detail')
# routers.register(r'v2/cuentaeje/representante-legal', UpdateRepresentanteLegal, basename='detail-cuenta-eje')
routers.register(r'v2/centro-costos/baja', BajaCentroCostoAdmin, basename='baja-centro-costos')
# routers.register(r'v2/services', Services, basename='create-services-superadmin')
routers.register(r'v3/AsiSer/create', ProductsServices, basename='create-services-superadmin')
routers.register(r'v2/admin', AdminGenericViewSet, basename='create-admin')
#routers.register(r'v2/admin/list', ListAdministrativeStaff, basename='List-Admin')
# CLIENTE EXTERNO
routers.register(r'v3/cliext/not', NotificarClienteExterno, basename="notificacionCE")
routers.register(r'v3/cliext/auth', AutorizarClienteExterno, basename="autorizacionCE")
routers.register(r'v3/cliext/list', clienteList_C_E, basename="clienteList_C_E")#BALAM LADO ADMIN SIN FILTRO
routers.register(r'v3/SolcliList/list', SolclientList, basename="SolclientList")#BALAM SOLICITUDES  LADO ADMIN SIN FILTRO
routers.register(r'v2/autorizar-documentos', AutorizarDocumentos, basename='Autorizar-documentos')
routers.register(r'v3/AddAdmCom/CRUD', AddAdministratives, basename='add_admins')
routers.register(r'v3/cliext/del', SolDismiss, basename='add_admins')

# CENTRO DE COSTOS
routers.register(r'v3/detail-centro-costos', DocumentosCentroCostosYRepresentanteLegal, basename='Detalle-centro-costos') ## correcto
routers.register(r'v3/NotCenCost/Auth', AutorizarCentroCostos, basename='Autorizar-centro-costos')
routers.register(r'v3/NotCenCost/notify', NotificarCentroCostos, basename='Notificacion-centro-costos')
# COLABORADORES
# routers.register(r'v3/Cols/Detail', ColaboratorDetail, basename='Detalle-de-colaborador')
# routers.register(r'v3/Cols/Auth', AuthorizeColab, basename='Autorizacion-colaborador')
# routers.register(r'v3/Cols/notify', NotifyColab, basename='Notificacion-colaborador')
# routers.register(r'v3/LisColAct/list', ListarColaboradoresActivos, basename='listar-colaborador')
# routers.register(r'v3/Cols/Sol', ListarSolicitudesColaborator, basename='listSol-colaborador')
# COCENTRADOS
routers.register(r'v3/Adm/Conct', ListContrados, basename='listSol-colaborador')
routers.register(r'v3/VerDocClaTra', VerifyDocumentsClaveTraspaso, basename='listSol-colaborador')
routers.register(r'v3/VerDocDomFis', VerifyDocumentsDomicilioFiscal, basename='listSol-colaborador')
routers.register(r'v3/VerDocCliExtFis', VerifyDocumentsClienteExternoFisico, basename='listSol-colaborador')
routers.register(r'v3/DetMovExtCli/get', DetailsMovementsExternClient, basename='listSol-colaborador')


urlpatterns = [
  path('v2/cuentaeje/list-admin/', ListAdminCuentaEje.as_view()),
  path('v3/LisCueEje/list/', ListCuentaEje.as_view()),
  path('v2/cuentaeje/detail/',  RetrieveCuentaEje.as_view()),
  path('v3/centro-costos/list-actives/', ListarCentroCostoActivos.as_view()),
  path('v3/centro-costos/list-solicitudes/', ListarSolicitudesCentroCostos.as_view()),
  path('v3/LisAdmCueEje/list/', ListAdminCuentaEje.as_view()),
  path('v3/DetAdmCueEje/get/', DetailAdminsCuentaEje.as_view()),
  path('v3/Admin/Dashboard/list', DashboardAdmin.as_view()),
  path('v3/LisPolAdm/list/', ListPolipayAdmins.as_view()),
  path('v3/LisCarCom/list/', ListCardCompany.as_view()),
  path('v3/LisCarAllCom/list/', ListCardsAllCompanys.as_view()),

  # """ CENTRO COSTOS """
  path('v3/DetCosCen/get/', DetailsCostCenter.as_view()),
  path('v3/ConCosCen/get/', ConsultarCostCenter.as_view()),
  path('v3/BajCosCen/get/', BajaCostCenter.as_view()),
  path('v3/ClaTraFinCosCen/get/', ClaveTraspasoCostCenter.as_view()),
  path('v3/DomFisCosCen/get/', DomicilioFiscalCostCenter.as_view()),
  path('v3/LisSolCosCen/list/', ListarSolicitudesCostCenter.as_view()),
  path('v3/LisCosCenActAdm/list/', ListCostCenterActiveAdmin.as_view()),
  path('v3/VerDocNewRep/ud/', VerifyDocumentsNewRepresentanteLegal.as_view()),
  path('v3/AsiCarCliExt/update/',  AsignarTarjetasClienteExterno.as_view()),
  path('v3/MovTarCliExt/list/',  MovimientosTarjetaClienteExterno.as_view()),
  path('v3/MovCueCliExt/list/',  MovimientosCuentaClienteExterno.as_view()),

  # """ COLABORADORES """
  path('v3/Cols/Sol/', ListarSolicitudesColaborator.as_view()),
  path('v3/VerDocCol/ug/', VerifyDocumentsColaborador.as_view()),
  path('v3/VerDocEdiCol/ug/', VerifyDocumentsEditColaborador.as_view()),
  path('v3/LisColAct/list', ListarColaboradoresActivos.as_view()),
] + routers.urls
