from typing import List

from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.response import Response

from MANAGEMENT.Utils.utils import to_dict_params
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.web.serializers.filter_serializer import *
from apps.transaction.exc import ParamsRaiseException, ParamsNotProvided, ParamStatusNotProvided
from apps.transaction.interface import ListData
from apps.transaction.json_render import JsonResponseDetailTransactionReceived, \
    JsonResponseDetailTransactionTercerosInidivual
from apps.transaction.models import transferencia, transferenciaProg
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Standard.errors_responses import MyHttpError


# (ChrGil 2022-02-02) Listado, filtrado y detallado de una transacción recibida
class ListTransactionReceivedSTP(ListData):
    def __init__(self, **kwargs):
        self._person_id = kwargs.get('person_id', None)
        self._transaction_id = kwargs.get('transaction_id', None)
        self._nombre_emisor = kwargs.get('nombre_emisor', '')
        self._clave_rastreo = kwargs.get('clave_rastreo', '')
        self._start_date = kwargs.get('start_date', dt.date.today() - dt.timedelta(days=91))
        self._end_date = kwargs.get('end_date', dt.date.today())
        self.defaul_size = kwargs.get('size', self.defaul_size)
        self._raise_params()

        if self._person_id:
            self.data = self._list

        if self._transaction_id:
            self.data = self._detail

    def _raise_params(self) -> NoReturn:
        if self._person_id and self._transaction_id:
            raise ParamsNotProvided(
                'Operación prohibida, no puede enviar clabe y transaction id como parametro de url al mismo tiempo')

        if not self._person_id and not self._transaction_id:
            raise ParamsNotProvided(
                'Operación prohibida, debe de enviar por lo menos un parametro (clabe) o (transaction_id)')

    @property
    def _list(self) -> List[Dict[str, Union[str, int, dt.datetime]]]:
        return transferencia.objects.select_related(
            'cuentatransferencia',
            'tipo_pago'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id=5,
            cuentatransferencia__persona_cuenta_id=self._person_id,
            nombre_emisor__icontains=self._nombre_emisor,
            clave_rastreo__icontains=self._clave_rastreo
        ).values(
            'id',
            'nombre_emisor',
            'monto',
            'clave_rastreo',
            'fecha_creacion'
        ).order_by('-fecha_creacion')

    @property
    def _detail(self) -> Dict[str, Union[str, int, dt.datetime]]:
        return transferencia.objects.filter(
            id=self._transaction_id
        ).values(
            'id',
            'nombre_beneficiario',
            'cta_beneficiario',
            'receiving_bank__institucion',
            'cuenta_emisor',
            'nombre_emisor',
            'transmitter_bank__institucion',
            'monto',
            'concepto_pago',
            'referencia_numerica',
            'fecha_creacion',
            'tipo_pago__nombre_tipo'
        ).first()


# (ChrGil 2021-10-13) Listado y filtrado de una transferencia recibida para una persona moral
# Endpoint: http://127.0.0.1:8000/transaction/web/v2/Received/list/?size=1000&person_id=1660
class TransferReceivedList(ListAPIView):
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            list_transaction = ListTransactionReceivedSTP(**data)
            self.pagination_class.page_size = list_transaction.defaul_size
        except (TypeError, ParamsRaiseException) as e:
            err = MyHttpError(message="Ocurrio un error al momento de listar las transacciones", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.get_paginated_response(self.paginate_queryset(list_transaction.data))


# (ChrGil 2022-02-02) Detallar la transaccion recibida
# Endpoint: http://127.0.0.1:8000/transaction/web/v2/DetTraRec/get/?transaction_id
class DetailTransactionReceived(RetrieveAPIView):
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        detail = ListTransactionReceivedSTP(**to_dict_params(request.query_params))
        log.json_request(request.query_params)
        json_response = JsonResponseDetailTransactionReceived(detail.data)
        return Response(json_response.json_data, status=status.HTTP_200_OK)


# (ChrGil 2022-02-13) Listar Ingresos dependiendo del producto
class ClassListTransactionAdminStatus(ListData):
    list_ingreso: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._status_type = kwargs.get('status_type', [3, 4])
        self._nombre_beneficiario = kwargs.get('nombre_beneficiario', '')
        self._clave_rastreo = kwargs.get('clave_rastreo', '')
        self.size = kwargs.get('size', self.defaul_size)
        self._start_date = kwargs.get('date1', dt.date.today() - dt.timedelta(days=91))
        self._end_date = kwargs.get('date2', dt.date.today())
        self.list_data = [self.render(**ingreso) for ingreso in self._list]

    def _raise_params(self) -> NoReturn:
        ...

    def _detail(self) -> NoReturn:
        ...

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return transferencia.objects.filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id__in=[1, 2],
            status_trans_id__in=list(self._status_type),
            nombre_beneficiario__icontains=self._nombre_beneficiario,
            clave_rastreo__icontains=self._clave_rastreo,
            user_autorizada__isnull=False
        ).values(
            'id',
            'empresa',
            'masivo_trans_id',
            'nombre_beneficiario',
            'cta_beneficiario',
            'monto',
            'clave_rastreo',
            'fecha_creacion',
            'date_modify',
            'status_trans_id',
            'status_trans__nombre',
        ).order_by('-date_modify')

    @staticmethod
    def render(**kwargs) -> Dict[str, Any]:
        return {
            "id": kwargs.get('id'),
            "empresa": kwargs.get('empresa'),
            "masivo_trans_id": kwargs.get('masivo_trans_id'),
            "nombre_beneficiario": kwargs.get('nombre_beneficiario'),
            "cta_beneficiario": kwargs.get('cta_beneficiario'),
            "monto": kwargs.get('monto'),
            "clave_rastreo": kwargs.get('clave_rastreo'),
            "fecha_creacion": kwargs.get('fecha_creacion'),
            "status_trans_id": kwargs.get('status_trans_id'),
            "status": kwargs.get('status_trans__nombre'),
        }


# (ChrGil 2021-10-13) Listado y filtrado de transferencias individuales por estado. (Liquidada, pendiente, cancelada)
class TransferStatusList(ListAPIView):
    pagination_class = PageNumberPagination

    # (ChrGil 2021-10-13) query_params (id, status_type, nombre_beneficiario, date1, date2, clave_rastreo)
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            lista = ClassListTransactionAdminStatus(**data)
            self.pagination_class.page_size = lista.size
            page = self.paginate_queryset(lista.list_data)
            return self.get_paginated_response(page)

        except TypeError as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ChrGil 2021-11-30) Detallar transacciones pendinetes
# Endpoint: http://127.0.0.1:8000/transaction/web/v2/DetPenTra/ud/
class DetailPendingTransaction(RetrieveUpdateAPIView):
    serializer_class = ChangeStatusSerializer

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            id: int = request.query_params['id']
            values: Dict = transferencia.filter_transaction.list_pending_transactions(transaction_id=id)
            return Response(values, status=status.HTTP_200_OK)

        except (MultiValueDictKeyError, FileNotFoundError, ValueError, TypeError) as e:
            err = MyHttpError("Ocurrio un error al cambiar el estado de la transacción", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError("Transferencia no encontrada", str(e), str(404))
            log.json_response(err.object_does_not_exist())
            return Response(err.object_does_not_exist(), status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            transaction_id: int = self.request.query_params['id']
            # demo_bool: int = self.request.query_params['demo_bool']
            demo_bool: int = True

            with atomic():
                log.json_request(request.data)
                context = {"transaction_id": transaction_id, "demo_bool": demo_bool}
                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                serializer.update_transfer(serializer.data)

                succ = MyHtppSuccess(message="Tu operación se realizo de manera satisfactoria")
                log.json_response(succ.standard_success_responses())
                return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)

        except MultiValueDictKeyError as e:
            err = MyHttpError("Asegurese de haber ingresado todos los parametros", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            err = MyHttpError("Ocurrio un error al liquidar la transacción", real_error=str(e))
            log.json_response(err.multi_value_dict_key_error())
            return Response(err.multi_value_dict_key_error(), status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            err = MyHttpError("Transferencia no encontrada", str(e), str(404))
            log.json_response(err.object_does_not_exist())
            return Response(err.object_does_not_exist(), status=status.HTTP_404_NOT_FOUND)


class ListTransferenciasTerceros(ListData):
    def __init__(self, **kwargs):
        self._cost_center_id = kwargs.get('cost_center_id', None)
        self._transaction_id = kwargs.get('transaction_id', None)
        self._nombre_emisor = kwargs.get('nombre_emisor', '')
        self._clabe_emisor = kwargs.get('clabe_emisor', '')
        self._nombre_beneficiario = kwargs.get('nombre_beneficiario', '')
        self._start_date = kwargs.get('start_date', dt.date.today() - dt.timedelta(days=91))
        self._end_date = kwargs.get('end_date', dt.date.today())
        self._status = kwargs.get('status', None)
        self.defaul_size = kwargs.get('size', self.defaul_size)

        if self._cost_center_id:
            self._raise_params()
            self.data = self._list

        if self._transaction_id:
            self.data = self._detail
            self.sheluded = None if not self.get_transaction_sheluded else self.get_transaction_sheluded.get(
                'fechaProgramada')

    def _raise_params(self) -> NoReturn:
        if self._cost_center_id and self._transaction_id:
            raise ParamsNotProvided(
                'Operación prohibida, no puede enviar clabe y transaction id como parametro de url al mismo tiempo')

        if not self._cost_center_id and not self._transaction_id:
            raise ParamsNotProvided(
                'Operación prohibida, debe de enviar por lo menos un parametro (clabe) o (transaction_id)')

        if not self._status:
            raise ParamStatusNotProvided("Operación prohibida, debe de enviar el tipo de estado de la transacción")

    @property
    def _list(self) -> List[Dict[str, Union[str, int, dt.datetime]]]:
        return transferencia.objects.select_related(
            'cuentatransferencia',
            'tipo_pago',
            'masivo_trans'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id=2,
            masivo_trans_id__isnull=True,
            status_trans_id=self._status,
            cuentatransferencia__persona_cuenta_id=self._cost_center_id,
            cuenta_emisor__icontains=self._clabe_emisor,
            nombre_beneficiario__icontains=self._nombre_beneficiario,
        ).values(
            'id',
            'nombre_beneficiario',
            'monto',
            'date_modify',
            'clave_rastreo',
            'status_trans__nombre',
        ).order_by('-fecha_creacion')

    @property
    def _detail(self) -> Dict[str, Union[str, int, dt.datetime]]:
        return transferencia.objects.filter(
            id=self._transaction_id
        ).values(
            'id',
            'clave_rastreo',
            'nombre_beneficiario',
            'cta_beneficiario',
            'receiving_bank__institucion',
            'transmitter_bank__institucion',
            'cuenta_emisor',
            'nombre_emisor',
            'empresa',
            'rfc_curp_emisor',
            'monto',
            'concepto_pago',
            'referencia_numerica',
            'fecha_creacion',
            'date_modify',
            'tipo_pago__nombre_tipo',
            'email',
            'emisor_empresa__name',
            'emisor_empresa__last_name',
            'user_autorizada__name',
            'user_autorizada__last_name'
        ).first()

    @property
    def get_transaction_sheluded(self) -> Union[Dict[str, Any], None]:
        return transferenciaProg.objects.filter(
            transferReferida_id=self._transaction_id).values('fechaProgramada').first()


# (ChrGil 2022-02-02) Ver detalles de una transacción a terceros individual
# Endpoint: http://127.0.0.1:8000/transaction/web/v2/DetTra/get/?transaction_id=12356
class DetailTransaction(RetrieveAPIView):
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        detail = ListTransferenciasTerceros(**to_dict_params(request.query_params))
        log.json_request(request.query_params)
        json_response = JsonResponseDetailTransactionTercerosInidivual(detail.data, sheluded=detail.sheluded)
        return Response(json_response.json_data, status=status.HTTP_200_OK)


# (ChrGil 2021-11-22) Listar transacción individual por estado y por centro de costos de lado del cliente
# (ChrGil 2021-11-22) parametros de URL (size, clabe, status, clabe_emisor, nombre_beneficiario, start_date, end_date)
# Endpoint: http://127.0.0.1:8000/transaction/web/v3/LisTraIndSta/list/?cost_center_id=1660
class ListTransactionIndividualStatus(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver transacciones individuales a terceros creadas",
                "Ver transacciones individuales a terceros pendientes",
                "Ver transacciones individuales a terceros canceladas",
                "Ver transacciones individuales a terceros enviadas",
                "Ver transacciones individuales a terceros devueltas"]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.query_params)
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            list_transfer = ListTransferenciasTerceros(**data)
            self.pagination_class.page_size = list_transfer.defaul_size
        except ParamsRaiseException as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", e.message)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.get_paginated_response(self.paginate_queryset(list_transfer.data))


class ComponentListTransactionSaldosWallet:
    """ Listar transacciones de SALDOS WALLET de lado del Admin"""

    def __init__(self, **kwargs):
        self.size = kwargs.get("size", 5)
        self.emisor = kwargs.get("nombre_emisor", '')
        self.clave_rastreo = kwargs.get("clave_rastreo", '')
        self.folio = kwargs.get("folio", None)
        self._start_date = kwargs.get('start_date', dt.date.today() - dt.timedelta(days=91))
        self._end_date = kwargs.get('end_date', dt.date.today())
        self.lista_data = self._list

    @property
    def _list(self) -> Dict[str, Any]:
        return transferencia.objects.select_related(
            'cuentatransferencia',
            'tipo_pago',
            'masivo_trans'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id=10,
            status_trans_id=1,
            nombre_emisor__icontains=self.emisor,
            clave_rastreo__icontains=self.clave_rastreo,
        ).values(
            'id',
            'nombre_emisor',
            'cuenta_emisor',
            'monto',
            'date_modify',
            'clave_rastreo',
            'status_trans_id',
        ).order_by(
            '-fecha_creacion'
        )


class ListTransactionSaldosWallet(ListAPIView):
    _list_transaction: ClassVar[ComponentListTransactionSaldosWallet] = ComponentListTransactionSaldosWallet

    def list(self, request, *args, **kwargs):
        try:
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            list_transfer = self._list_transaction(**data)
            self.pagination_class.page_size = list_transfer.size
        except ParamsRaiseException as e:
            err = MyHttpError("Los parametros de filtrado no coinciden con los esperados", e.message)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.get_paginated_response(self.paginate_queryset(list_transfer.lista_data))
