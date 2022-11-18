from django.urls import path

from rest_framework import routers

from apps.transaction.api.web.views.Transacciones_views import *
from apps.transaction.api.web.views.sheduled import CreateDispersionSheluded
from apps.transaction.api.web.views.views_dashboard_transaction import DashBoardDispersa, DashBoardTransaction
from apps.transaction.api.web.views.views_export_transfer_status import ExportExcelTransactionStatus, \
    ExportExcelTransactionStatusAdmin, ExportExcelTransactionSaldosWallet
from apps.transaction.api.web.views.views_adelante_zapopan import CreateBeneficiarioAdelanteZapopan, AltaBrigadistaZapopan
from apps.transaction.api.web.views.views_dispersiones_masivas import DispersionesMasivasIndividuales, \
    CancelMassiveDispersionSheduled
from apps.transaction.api.web.views.views_transaccion_recibida_manual import CreateTransactionReceived, \
    CreateTransactionReceivedFisicPerson
from apps.transaction.api.web.views.views_transaction_individual import *
from apps.transaction.api.web.views.views_dispersiones import *
from apps.transaction.api.web.views.views_listar_movimientos import *
from apps.transaction.api.web.views.views_transaction_massive import *
from apps.transaction.api.web.views.views_transaction_export_file import *
from apps.transaction.api.web.views.views_transaction_potpo import CreateTransactionPolipayToPolipayV2, \
    ListTransactionPolipayToPolipayStatus

router = routers.DefaultRouter()
router.register(r'v2/transferenciaM', transaccionesMasivasExcel, basename='crear excel')
router.register(r'v2/transacciones', Transacciones, basename='transaccion')
router.register(r'v2/statusTransaction', changeStatusTransactions, basename='cambiar-estado-transaccion')
router.register(r'v2/ListAllBanks', ListAllBanks, basename='listar-bancos')
router.register(r'v2/detailDispercionIndividual', DetailDispercionIndividual, basename='listar-detalles')
router.register(r'v2/Transaction/Create/Recibidas', CreateTransactionReceived, basename='Transaction-rec')
router.register(r'v2/Transaction/Create/Recibidas/persona_fisica', CreateTransactionReceivedFisicPerson, basename='Transaction-rec')
router.register(r'v2/TraPolThi/Create', CreateTransactionToThirdPerson, basename='Transaction-Polipay-Terceros')
router.register(r'v2/Detail-Transaction/Received', DetailTransactionRecieved, basename='listar-detalles')
router.register(r'v2/Dispersion/add', DispersionV2, basename='listar-detalles')
router.register(r'v3/CreDisIndMas/create', DispersionesMasivasIndividuales, basename='listar-detalles')
router.register(r'v2/Documento/create', ComprobanteDisInd, basename='listar-detalles')
router.register(r'v2/maspdf/rd', pdfmasivas, basename='descargar pdf')
router.register(r'v3/CanDisMasPro/update', CancelMassiveDispersionSheduled, basename='cancel-dispersion')

router.register(r'v2/CanTra/update', CancelTransactionPolipayToThird, basename='cancelar')
# router.register(r'v2/TraPolToPol/create', CreateTransactionPolipayToPolipay, basename='Transaccion-Polipay-Polipay')
router.register(r'v2/TraPolToPol/create', CreateTransactionPolipayToPolipayV2, basename='Transaccion-Polipay-Polipay')
router.register(r'v3/MasTra/create', MassTransferGenericViewSet, basename='transferencia-masiva')

router.register(r'v3/MovEgr/list', MovimientosEgresos, basename='Movimientos-egresos')
router.register(r'v3/MovIng/list', MovimientosIngresos, basename='Movimientos-ingresos')
router.register(r'v3/MovIngEgr/list', MovimientosIngresosEgresos, basename='Movimientos-todos')

router.register(r'v3/EstCueExc/get',GenerarExcel, basename='Crear estado de cuenta Excel')
router.register(r'v3/EstCuePdf/get',DescargarPdf, basename='Crear estado de pdf')
router.register(r'v3/ComTra/create', ComprobanteTransferPolipayToThird, basename='crear-beneficiario')
router.register(r'v3/TraOwnAcc/create', CreateTransactionBetweenOwnAccounts, basename='Transaccion-Polipay-Polipay')
router.register(r'v3/CanDisShe/update', CancelDispersionSheduled, basename='Transaccion-Polipay-Polipay')


router.register(r'v3/DisExc/get',ExcelDispersion, basename='Crear estado de cuenta Excel')

# (ChrGil 2022-01-06) TMP, alta brigadista y beneficiario para Adelante Zapopan
router.register(r'v3/CreDenAdeZap/create', CreateBeneficiarioAdelanteZapopan, basename='crear-beneficiario')
router.register(r'v3/AltBriZap/create', AltaBrigadistaZapopan, basename='crear-beneficiario')

urlpatterns = [
    # path('v2/generate/excel/', GenerateExcel.as_view(), name='generate-filter-individual-excel'),
    path('v2/RecNomBen/list/', RecomendarNombreBeneficiario.as_view()),
    path('v2/LisStaDis/list/', ListStatusDispersion.as_view()),
    # path('v2/list/movimiento-egresos/', ListMovimientoEgresos.as_view()),
    path('v2/LisDisMas/list/', ListDispersionesMasivasEstado.as_view()),
    path('v2/DetDisMas/list/', DetailDispersionesMassive.as_view()),
    path('v2/TraRecCom/list/', ListTransactionReceivedCompany.as_view()),
    path('v2/TraRecPer/list/', ListTransactionReceivedFisicPerson.as_view()),
    path('v2/ShoDetDisMas/get/', ShowDetailsDispersionMasiva.as_view()),
    path('v2/VerMon/get/', VerifyMonto.as_view()),
    path('v2/cuenta-eje/list-cuentaeje/', GetCuentaEje.as_view()),
    path('v2/LisCosCen/list/', GetCostCenter.as_view()),
    path('v2/cuenta-eje/list-persona-fisica/', GetFisicPerson.as_view()),
    path('v2/LisIng/list/', ListIngresosRazonSocial.as_view()),
    path('v2/LisEgr/list/', ListEgresosRazonSocial.as_view()),
    path('v2/LisEgrIng/list/', ListIngresosEgresosRazonSocial.as_view()),
    path('v2/Received/list/', TransferReceivedList.as_view()),
    path('v2/DetTraRec/get/', DetailTransactionReceived.as_view()),
    path('v2/TraSta/list/', TransferStatusList.as_view()),
    path('v2/DetPenTra/ud/', DetailPendingTransaction.as_view()),
    path('v2/ShoDetDis/get/', ShowDetailDispersion.as_view()),
    path('v2/DetTra/get/',  DetailTransaction.as_view()),
    path('v2/maspdf/get', CrearPDFMasivas.as_view()),
    path('v3/LisTraMasSta/list/', ListTransMassiveStatus.as_view()),
    path('v3/DetTraMas/list/', DetailTransactionMassive.as_view()),
    path('v3/DetInfTraMas/get/', DetailInfoTransactionMassive.as_view()),
    path('v3/CanBulTra/update/', CancelBulkTransaction.as_view()),
    path('v3/AutBulTra/update/', AuthorizeBulkTransaction.as_view()),
    path('v3/CarSeaDis/list/', CardSearchDispersion.as_view()),
    path('v3/ShoMorTraMas/get/', ShowMoreDetailTransactionMassive.as_view()),
    path('v3/LisTraIndSta/list/', ListTransactionIndividualStatus.as_view()),
    path('v3/LisTraSalWal/list/', ListTransactionSaldosWallet.as_view()),
    path('v2/TraPolToPolSen/list/', ListTransactionPolipayToPolipaySend.as_view()),
    path('v2/TraPolToPolRec/list/', ListTransactionPolipayToPolipayReceived.as_view()),
    path('v2/TraPolToPolStatus/list/', ListTransactionPolipayToPolipayStatus.as_view()),
    path('v3/TraOwnAcc/list/', ListTransactionBeetweenOwnAccounts.as_view()),
    path('v2/DetTraPolToPolSen/get/', DetailTransactionPolipayToPolipaySend.as_view()),
    path('v3/DetTraOwnAcc/get/', DetailTransactionOwnAccounts.as_view()),
    path('v3/AutTraPol/update/', AuthorizeTransactionPolipayToThird.as_view()),
    path('v3/ExpXls/get/', ExportExcelTransactionStatus.as_view()),
    path('v3/ExpXlsAdm/get/', ExportExcelTransactionStatusAdmin.as_view()),
    path('v3/ExpXlsSalWal/list/', ExportExcelTransactionSaldosWallet.as_view()),
    path('v3/CreDisShe/get/', CreateDispersionSheluded.as_view()),
    path('v3/ExportFile/csv/get', ExportDataToCSV.as_view()),
    path('v3/DashDis/list/', DashBoardDispersa.as_view()),
    path('v3/DashTra/list/', DashBoardTransaction.as_view()),
    path('v3/TraOwnAccDash/list', ListTransactionOwnAccounts.as_view()),
    path('v3/FilterAccount/list', FilterAccountsCostCenters.as_view()),

] + router.urls
