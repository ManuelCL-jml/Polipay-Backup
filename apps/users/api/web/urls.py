from django.urls import path

from rest_framework import routers

from .views.cliente_externo_view import PersontaExterna
from .views.cliente_externo_view import *
from .views.inntec_view import *
from .views.user_views import *
from .views.documentos_view import *

# from apps.users.api.web.views.cuenta_eje_views import *
# from apps.users.api.web.views.centro_costos_views import *

routers = routers.SimpleRouter()

routers.register(r'v2/documents', Document, basename='create-documentos')
routers.register(r'v2/documents/authorization', AuthorizeDocuments, basename='create-autorizacion')
routers.register(r'v2/password/change', ChangePassword, basename='change-password')
routers.register(r'v2/password/recover', RecoverPassword, basename='recover-password')
routers.register(r'v2/resend/email', ResendEmail, basename='resend-email')
routers.register(r'v2/login/user', Login, basename='user-login')
routers.register(r'v2/login/check-code', LoginCheckCodeClient, basename='user-login-check-code')
routers.register(r'v2/login/new-password', ChangePasswordNew, basename='change-password-new')
routers.register(r'v3/SendSMSNip/create', EnviarCodigoPorSMS, basename='Enviar-nip-SMS')
#routers.register(r'v3/CheckNip/create', CompararCodigo, basename='Verificar-nip')
routers.register(r'v2/personal-externo', PersontaExterna, basename='personal-exerno')
routers.register(r'v2/personal-externa-detail', DetailPersonaExterna, basename='Detail')
routers.register(r'v2/buscar/tarjeta-inntec', BuscarNumeroTarjetaInntec, basename='buscar-tareja-inntec')
routers.register(r'v2/asignar/tarjeta-persona-externa', AsignarTarjetaInntecPersonalExterno,
                 basename='asignar-tareja-inntec-personal-externo')
routers.register(r'v2/asignar/tarjeta-cuenta-eje', AsignarTarjetaInnteCuentaEje,
                 basename='asignar-tareja-inntec-cuenta-eje')

routers.register(r'v3/SendCallNip/create', SendCodeCall, basename="Enviar-nip-llamada")
routers.register(r'v3/LayPerExtMas/list', LayoutPersonalExternoMasivo, basename="Descargar-Layout")
routers.register(r'v3/PerExtMas/create', PersonalExternoMasivo, basename="Crear-personal-masivo")

routers.register(r'v3/LayPerExtMasDes/cr', LayoutAsignarTarjetaPersonalExterno, basename="crear-excel-beneficiarios-sin-tarjeta")
routers.register(r'v3/BenCenCos/cud', beneficiarios_centro_costos, basename="Crear,editar y eliminar beneficiarios por centro de costo")

# Pruebas
routers.register(r'v3/buscar/tarjeta-inntec-pruebas', BuscarNumeroTarjetaInntecPrueba, basename='buscar-tareja-inntec-pruebas')
routers.register(r'v3/asignar/tarjeta-cuenta-eje-pruebas', AsignarTarjetaInnteCuentaEjePrueba,
                 basename='asignar-tareja-inntec-cuenta-eje-prueba')
routers.register(r'v3/prueba-inntecv2', PruebaDeTarjeta, basename='buscar-tareja-inntec-pruebas')
######### 
            

urlpatterns = [
    path('v2/FilPerExt/list/', FiltroPersonalExterno.as_view()),
    path('v2/LisPerExt/list/', ListarPersonalExterno.as_view()),
    path('v2/buscar/tarjeta-cuenta-eje/', BuscarNumeroTarjetaCuentaEje.as_view()),
    path('v2/buscar/movimientos/tarjeta/', MovimientosTarjeta.as_view()),
    path('v2/buscar/saldo/tarjeta/', BuscarSaldosTarjetaInntec.as_view()),
    path('v2/CheCarBal/get/', CheckCardBalance.as_view()),
    path('v2/buscar/movimientos/cuenta/', MovimientosCuentaView.as_view()),
    path('v2/DowPdf/get/', DownloadPdf.as_view()),
    path('v2/buscar/movimientos/cuenta/detalles/', DetallesMovimientosCuenta.as_view()),
    path('v3/BenCenCos/list', ListBeneficiariosCentroCostos.as_view()),
    path('v3/BenCenCosFil/list', FiltroPersonalExternoCentroCosto.as_view()),
] + routers.urls
