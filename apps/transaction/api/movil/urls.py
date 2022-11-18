from django.urls import path

from rest_framework import routers

from apps.transaction.api.movil.views.createTipoTrasnferencia import *
from apps.transaction.api.movil.views.createTransaction import *
from .views.createTransaction import *
from .views.list import *
# from transaction.api.movil.views.createStatus import *
# from transaction.api.movil.views.createBancos import *


router = routers.SimpleRouter()

router.register(r'v2/list/types', listTypes, basename='listTypes')
router.register(r'v2/MovHis/get', MovementHistory, basename='hitsorial_movimientos_tarjeta')
router.register(r'v2/list/history', getHistorial, basename='getHistorial')
router.register(r'v3/MovementReport/send', SendMovementReport, basename='SendMovementReport')
router.register(r'v2/create/transfer', createUserTransactionMovil, basename='transfer')

router.register(r'v2/tipo_transferencia',tiposTransferencia, basename='tipo_transferencia')
router.register(r'v2/prueba', createUserTransactionMovil, basename='prueba')
router.register(r'v2/ckeck/amount', prueba, basename='CheckTransaction')
router.register(r'v2/list/transafer/template', lisTransactionTemplate, basename='lisTransactionTemplate')
urlpatterns = router.urls
