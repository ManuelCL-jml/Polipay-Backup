import datetime as dt
from os import remove
from typing import ClassVar, NoReturn, List, Dict, Any

from django.core.files import File
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import RetrieveAPIView
from rest_framework import status
from rest_framework.response import Response

from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.ExportExcel.web.EstadosTransacciones.export_transacation_status import CreateExcel
from MANAGEMENT.Utils.utils import remove_asterisk
from apps.transaction.exc import ParamsNotProvided, ParamStatusNotProvided, ParamsRaiseException
from apps.transaction.models import transferencia
from apps.users.models import documentos, persona


# (ChrGil 2022-03-28) Exportar todas las transacciones, por tipo de pago
# (ChrGil 2022-03-28) estado o por filtro
class ExportDataExcel:
    _default_start_date: ClassVar[dt.date] = dt.date(2000, 1, 1)
    list_data: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self.razon_social_id = kwargs.get('razon_social_id', None)
        self._masivo_id = kwargs.get('masivo_trans_id', None)
        self._tipo_pago_id = kwargs.get('tipo_pago_id', None)
        self._clave_rastreo = kwargs.get('clave_rastreo', '')
        self._nombre_emisor = kwargs.get('nombre_emisor', '')
        self._clabe_emisor = kwargs.get('clabe_emisor', '')
        self._nombre_beneficiario = kwargs.get('nombre_beneficiario', '')
        self._start_date = kwargs.get('start_date', self._default_start_date)
        self._end_date = kwargs.get('end_date', dt.date.today())
        self._status = kwargs.get('status', None)
        self._raise_params()

        if kwargs.get('masivo_trans_id'):
            self.list_data = [self._render(**transfer) for transfer in self._list(masivo_trans_id=self._masivo_id)]

        if not kwargs.get('masivo_trans_id'):
            self.list_data = [self._render(**transfer) for transfer in self._list(masivo_trans_id__isnull=True)]

    def _raise_params(self) -> NoReturn:
        if not self.razon_social_id:
            raise ParamsNotProvided(
                'Operación prohibida, debe de enviar por lo menos un parametro (razon social id) o (transaction_id)')

        if not self._status:
            raise ParamStatusNotProvided("Operación prohibida, debe de enviar el tipo de estado de la transacción")

        if not self._tipo_pago_id:
            raise ParamStatusNotProvided("Operación prohibida, debe de enviar el tipo de pago")

    def _list(self, **kwargs) -> List[Dict[str, Any]]:
        return transferencia.objects.select_related(
            'tipo_pago',
            'cuentatransferencia',
            'receiving_bank',
            'transmitter_bank',
            'status_trans'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            status_trans_id=self._status,
            cuentatransferencia__persona_cuenta_id=self.razon_social_id,
            cuenta_emisor__icontains=self._clabe_emisor,
            nombre_beneficiario__icontains=self._nombre_beneficiario,
            nombre_emisor__icontains=self._nombre_emisor,
            tipo_pago_id=self._tipo_pago_id,
            clave_rastreo__icontains=self._clave_rastreo,
            **kwargs
        ).values(
            "id",
            "cuenta_emisor",
            "nombre_emisor",
            "cta_beneficiario",
            "receiving_bank__institucion",
            "clave_rastreo",
            "nombre_beneficiario",
            "rfc_curp_beneficiario",
            "tipo_pago__nombre_tipo",
            "t_ctaBeneficiario",
            "monto",
            "concepto_pago",
            "referencia_numerica",
            "transmitter_bank__institucion",
            "fecha_creacion",
            "nombre_emisor",
            "tipo_pago__nombre_tipo",
            "tipo_pago_id",
            "date_modify",
        )

    @staticmethod
    def _render(**kwargs):
        return {
            "id": kwargs.get("id"),
            "cuenta_ordenante": kwargs.get("cuenta_emisor"),
            "nombre": remove_asterisk(kwargs.get("nombre_emisor")),
            "cuenta": kwargs.get("cta_beneficiario"),
            "banco": kwargs.get("receiving_bank__institucion"),
            "claverastreo": kwargs.get("clave_rastreo"),
            "nombrebeneficiario": remove_asterisk(kwargs.get("nombre_beneficiario")),
            "rfcurp": kwargs.get("rfc_curp_beneficiario"),
            "tipoPago": kwargs.get("tipo_pago__nombre_tipo"),
            "tipoCuenta": kwargs.get("t_ctaBeneficiario"),
            "monto": kwargs.get("monto"),
            "conceptopago": kwargs.get("concepto_pago"),
            "referencianumerica": kwargs.get("referencia_numerica"),
            "institucionoperante": kwargs.get("transmitter_bank__institucion"),
            "date_created": kwargs.get("fecha_creacion"),
            "company": kwargs.get("nombre_emisor"),
            "typetransaction": kwargs.get("tipo_pago__nombre_tipo"),
            "fecha_operacion": kwargs.get("date_modify"),
        }


class UpDocumentAWS:
    location_file_aws: ClassVar[str]

    def __init__(self, owner: persona, excel: CreateExcel):
        self._owner = owner
        self._excel = excel
        self.location_file_aws = self._up_document.get_url_aws_document()

    @property
    def _create(self) -> documentos:
        return documentos.objects.create_document(
            owner=54,
            tipo=20,
            comment='Exportar Transacciones por estado'
        )

    @property
    def _up_document(self) -> documentos:
        instance = self._create

        with open(self._excel.file_name, 'rb') as file:
            instance.documento = File(file)
            instance.save()

        remove(self._excel.file_name)
        return instance


# Endpoint: http://127.0.0.1:8000/transaction/web/v3/ExpXls/get/?cost_center_id=&tipo_pago_id=nombre_emisor=clabe_emisor=nombre_beneficiario=start_date=end_date=status=&
class ExportExcelTransactionStatus(RetrieveAPIView):

    @method_decorator(cache_page(60 * 0.1))
    def retrieve(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}

            data_to_export = ExportDataExcel(**data)
            export = CreateExcel(data_to_export.list_data, data_to_export.razon_social_id)
            document = UpDocumentAWS(admin, export)

        except (ValueError, ParamsRaiseException) as e:
            err = MyHttpError('Ocurrio un error al exportar el documento', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            msg = 'El listado se exporto a xlsx de manera satisfactoria'
            scc = MyHtppSuccess(message=msg, extra_data=document.location_file_aws)
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2022-03-28) Exportar todas las transacciones, por tipo de pago
# (ChrGil 2022-03-28) estado o por filtro
class ExportTransactionPendientesDataExcelAdmin:
    _default_start_date: ClassVar[dt.date] = dt.date(2000, 1, 1)
    list_data: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._clave_rastreo = kwargs.get('clave_rastreo', '')
        self._nombre_emisor = kwargs.get('nombre_emisor', '')
        self._clabe_emisor = kwargs.get('clabe_emisor', '')
        self._nombre_beneficiario = kwargs.get('nombre_beneficiario', '')
        self._start_date = kwargs.get('date1', self._default_start_date)
        self._end_date = kwargs.get('date2', dt.date.today())
        self._status = kwargs.get('status_type', None)
        self.list_data = [self._render(**transfer) for transfer in self._list]

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return transferencia.objects.select_related(
            'tipo_pago',
            'cuentatransferencia',
            'receiving_bank',
            'transmitter_bank',
            'status_trans'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id__in=[1, 2],
            status_trans_id=self._status,
            user_autorizada__isnull=False,
            clave_rastreo__icontains=self._clave_rastreo,
            nombre_beneficiario__icontains=self._nombre_beneficiario,
        ).values(
            "id",
            "cta_beneficiario",
            "nombre_beneficiario",
            "rfc_curp_beneficiario",
            "t_ctaBeneficiario",
            "receiving_bank__institucion",
            "clave_rastreo",
            "tipo_cuenta",
            "monto",
            "concepto_pago",
            "referencia_numerica",
            "empresa",
            "t_ctaEmisor",
            "nombre_emisor",
            "cuenta_emisor",
            "rfc_curp_emisor",
            "transmitter_bank__institucion",
            "fecha_creacion",
            "date_modify",
            "email",
            "programada",
            "saldo_remanente",
            "tipo_pago__nombre_tipo",
            "tipo_pago_id",
            "date_modify",
            "status_trans__nombre"
        )

    @staticmethod
    def _render(**kwargs):
        return {
            "id": kwargs.get("id"),
            "cuenta_ordenante": kwargs.get("cuenta_emisor"),
            "nombre": remove_asterisk(kwargs.get("nombre_emisor")),
            "cuenta": kwargs.get("cta_beneficiario"),
            "banco": kwargs.get("receiving_bank__institucion"),
            "claverastreo": kwargs.get("clave_rastreo"),
            "nombrebeneficiario": remove_asterisk(kwargs.get("nombre_beneficiario")),
            "rfcurp": kwargs.get("rfc_curp_beneficiario"),
            "tipoPago": kwargs.get("tipo_pago__nombre_tipo"),
            "tipoCuenta": kwargs.get("t_ctaBeneficiario"),
            "monto": kwargs.get("monto"),
            "conceptopago": kwargs.get("concepto_pago"),
            "referencianumerica": kwargs.get("referencia_numerica"),
            "institucionoperante": kwargs.get("transmitter_bank__institucion"),
            "date_created": kwargs.get("fecha_creacion"),
            "company": kwargs.get("nombre_emisor"),
            "typetransaction": kwargs.get("tipo_pago__nombre_tipo"),
            "fecha_operacion": kwargs.get("date_modify"),
            "estado": kwargs.get("status_trans__nombre"),
        }


# Endpoint: http://127.0.0.1:8000/transaction/web/v3/ExpXls/get/?cost_center_id=&tipo_pago_id=nombre_emisor=clabe_emisor=nombre_beneficiario=start_date=end_date=status=&
class ExportExcelTransactionStatusAdmin(RetrieveAPIView):
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}

            data_to_export = ExportTransactionPendientesDataExcelAdmin(**data)
            export = CreateExcel(data_to_export.list_data, 54)
            document = UpDocumentAWS(admin, export)

        except (ValueError, ParamsRaiseException) as e:
            err = MyHttpError('Ocurrio un error al exportar el documento', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            msg = 'El listado se exporto a xlsx de manera satisfactoria'
            scc = MyHtppSuccess(message=msg, extra_data=document.location_file_aws)
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)


# (ChrGil 2022-03-28) Exportar todas las transacciones, por tipo de pago
# (ChrGil 2022-03-28) estado o por filtro
class ExportTransactionSaldosWalletDataExcelAdmin:
    _default_start_date: ClassVar[dt.date] = dt.date(2000, 1, 1)
    list_data: ClassVar[List[Dict[str, Any]]]

    def __init__(self, **kwargs):
        self._clave_rastreo = kwargs.get('clave_rastreo', '')
        self._nombre_emisor = kwargs.get('nombre_emisor', '')
        self._start_date = kwargs.get('start_date', self._default_start_date)
        self._end_date = kwargs.get('end_date', dt.date.today())
        self.list_data = [self._render(**transfer) for transfer in self._list]

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return transferencia.objects.select_related(
            'tipo_pago',
            'cuentatransferencia',
            'receiving_bank',
            'transmitter_bank',
            'status_trans'
        ).filter(
            Q(fecha_creacion__date__gte=self._start_date) &
            Q(fecha_creacion__date__lte=self._end_date)
        ).filter(
            tipo_pago_id=10,
            clave_rastreo__icontains=self._clave_rastreo,
            nombre_emisor__icontains=self._nombre_emisor,
        ).values(
            "id",
            "cta_beneficiario",
            "nombre_beneficiario",
            "rfc_curp_beneficiario",
            "t_ctaBeneficiario",
            "receiving_bank__institucion",
            "clave_rastreo",
            "tipo_cuenta",
            "monto",
            "concepto_pago",
            "referencia_numerica",
            "empresa",
            "t_ctaEmisor",
            "nombre_emisor",
            "cuenta_emisor",
            "rfc_curp_emisor",
            "transmitter_bank__institucion",
            "fecha_creacion",
            "date_modify",
            "email",
            "programada",
            "saldo_remanente",
            "tipo_pago__nombre_tipo",
            "tipo_pago_id",
            "date_modify",
            "status_trans__nombre"
        )

    @staticmethod
    def _render(**kwargs):
        return {
            "id": kwargs.get("id"),
            "cuenta_ordenante": kwargs.get("cuenta_emisor"),
            "nombre": remove_asterisk(kwargs.get("nombre_emisor")),
            "cuenta": kwargs.get("cta_beneficiario"),
            "banco": kwargs.get("receiving_bank__institucion"),
            "claverastreo": kwargs.get("clave_rastreo"),
            "nombrebeneficiario": remove_asterisk(kwargs.get("nombre_beneficiario")),
            "rfcurp": kwargs.get("rfc_curp_beneficiario"),
            "tipoPago": kwargs.get("tipo_pago__nombre_tipo"),
            "tipoCuenta": kwargs.get("t_ctaBeneficiario"),
            "monto": kwargs.get("monto"),
            "conceptopago": kwargs.get("concepto_pago"),
            "referencianumerica": kwargs.get("referencia_numerica"),
            "institucionoperante": kwargs.get("transmitter_bank__institucion"),
            "date_created": kwargs.get("fecha_creacion"),
            "company": kwargs.get("nombre_emisor"),
            "typetransaction": kwargs.get("tipo_pago__nombre_tipo"),
            "fecha_operacion": kwargs.get("date_modify"),
            "estado": kwargs.get("status_trans__nombre"),
        }


class ExportExcelTransactionSaldosWallet(RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}

            data_to_export = ExportTransactionSaldosWalletDataExcelAdmin(**data)
            export = CreateExcel(data_to_export.list_data, 54)
            document = UpDocumentAWS(admin, export)

        except (ValueError, ParamsRaiseException) as e:
            err = MyHttpError('Ocurrio un error al exportar el documento', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            msg = 'El listado se exporto a xlsx de manera satisfactoria'
            scc = MyHtppSuccess(message=msg, extra_data=document.location_file_aws)
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)
