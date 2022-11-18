import datetime as dt
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Union, ClassVar, List, Any, NoReturn

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, DatabaseError
from django.db.models import Q
from django.db.transaction import atomic
from rest_framework import viewsets, status
from rest_framework.response import Response

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.Utils.utils import calculate_commission, add_iva
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.commissions.models import Commission, Commission_detail
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.web.serializers.serializers_transaccion_recibida_manual import \
    SerializerTransactionPolipayComission, CreateTransactionReceivedIn, SerializerCreateTransactionReceivedFisicPerson
from apps.transaction.models import detalleTransferencia, transferencia
from apps.users.models import cuenta, persona, grupoPersona
from polipaynewConfig.settings import COST_CENTER_POLIPAY_COMISSION


class DepositAmountRecived(ABC):
    @abstractmethod
    def _deposit_amount(self) -> NoReturn:
        ...


@dataclass
class ResquestDataTransaccionRecibidaManual:
    request_data: Dict[str, Union[str, int, float]]

    @property
    def get_folio_operacion(self) -> int:
        return self.request_data.get('id')

    @property
    def get_cuenta_beneficiario(self) -> str:
        return self.request_data.get('cta_beneficiario')

    @property
    def get_fecha_operacion(self) -> int:
        return self.request_data.get('date_modify')

    @property
    def get_hour(self) -> int:
        return self.request_data.get('hora')

    @property
    def get_institucion_ordenante(self) -> int:
        return self.request_data.get('transmitter_bank_id')

    @property
    def get_institucion_beneficiaria(self) -> int:
        return self.request_data.get('receiving_bank_id')

    @property
    def get_clave_rastreo(self) -> str:
        return self.request_data.get('clave_rastreo')

    @property
    def get_nombre_ordenante(self) -> str:
        return self.request_data.get('nombre_emisor')

    @property
    def get_tipo_cuenta_ordenante(self) -> int:
        return self.request_data.get('tipoCuentaOrdenante')

    @property
    def get_monto(self) -> float:
        return self.request_data.get('monto')

    @property
    def get_cuenta_ordenante(self) -> str:
        return self.request_data.get('cuenta_emisor')

    @property
    def get_empresa(self) -> str:
        return self.request_data.get('empresa')

    @property
    def get_nombre_beneficiario(self) -> str:
        return self.request_data.get('nombre_beneficiario')

    @property
    def get_rfc_curp_beneficiario(self) -> str:
        return self.request_data.get('rfc_curp_beneficiario')

    @property
    def get_concepto_pago(self) -> str:
        return self.request_data.get('concepto_pago')

    @property
    def get_referencia_numerica(self) -> int:
        return self.request_data.get('referencia_numerica')

    @property
    def get_all_request_data(self) -> Dict[str, Any]:
        return self.request_data


class GetInfoBeneficiario:
    # (ChrGil 2022-01-12) Obtiene toda la información del beneficiario, sea Moral o Físico

    beneficiario_info: ClassVar[Dict[str, Any]]
    info_admins: ClassVar[List[Dict[str, Any]]]
    beneficiario_account_info: ClassVar[Dict[str, int]]
    cuenta_eje_id: ClassVar[Dict[str, int]]
    _admins_id_cuenta_eje: ClassVar[List[int]]

    def __init__(self, cost_center_id: int):
        self._cost_center_id = int(cost_center_id)
        self.beneficiario_account_info = None
        self._get_info_account()
        self._get_info_beneficiario()
        self._get_cuenta_eje_info()

        if self.beneficiario_info.get('tipo_persona_id') == 1:
            self._get_admin_id_cuenta_eje()
            self._get_info_admins()

    @property
    def get_monto_actual(self) -> Dict[str, float]:
        return cuenta.objects.filter(persona_cuenta_id=self._cost_center_id).values('monto').first()

    def _get_info_account(self) -> NoReturn:
        if isinstance(self._cost_center_id, int):
            self.beneficiario_account_info = cuenta.objects.filter(
                persona_cuenta_id=self._cost_center_id, is_active=True
            ).values('persona_cuenta_id', 'id', 'cuentaclave', 'monto').first()

        if not self.beneficiario_account_info:
            raise ValueError("Cuenta clabe no valida o no existe")

    def _get_info_beneficiario(self) -> NoReturn:
        self.beneficiario_info = persona.objects.filter(
            id=self.beneficiario_account_info.get('persona_cuenta_id'), state=True
        ).values('id', 'name', 'last_name', 'email', 'tipo_persona_id', 'token_device', 'rfc').first()

        if not self.beneficiario_info:
            raise ValueError("Beneficiario no valido o no existe")

    def _get_cuenta_eje_info(self) -> NoReturn:
        _razon_social_id = grupoPersona.objects.filter(
            person_id=self.beneficiario_account_info.get('persona_cuenta_id'), relacion_grupo_id__in=[5, 9]).values(
            'empresa_id').first()

        if not _razon_social_id:
            raise ValueError('Beneficiario no valido o no existe')

        try:
            self.cuenta_eje_id = grupoPersona.objects.values('empresa_id').get(
                person_id=_razon_social_id.get('empresa_id'), relacion_grupo_id=5)

            print(self.cuenta_eje_id)
        except ObjectDoesNotExist as e:
            self.cuenta_eje_id = _razon_social_id

    def _get_admin_id_cuenta_eje(self) -> NoReturn:
        self._admins_id_cuenta_eje = grupoPersona.objects.filter(
            empresa_id=self.cuenta_eje_id.get('empresa_id'), person__state=True).filter(
            Q(relacion_grupo_id=1) | Q(relacion_grupo_id=3)
        ).values_list('person_id', flat=True)

    def _get_info_admins(self) -> NoReturn:
        self.info_admins = list(persona.objects.filter(
            id__in=self._admins_id_cuenta_eje).values('email', 'name'))


# (ChrGil 2022-01-31) Obtiene la comision que se le va a cobrar al beneficiario
class GetCommissionsFromPerson:
    info: ClassVar[Dict[str, Union[int, Decimal]]]
    _servicio_transferencias: ClassVar[int] = 1

    def __init__(self, beneficiario: GetInfoBeneficiario):
        self.beneficiario = beneficiario
        self._get_comission_person()
        print(self.info)

    def _get_comission_person(self) -> NoReturn:
        company_id = self.beneficiario.cuenta_eje_id.get('empresa_id')
        self.info = Commission.objects.get_info_comission_manual(owner=company_id, service_id=self._servicio_transferencias)


# (ChrGil 2022-01-11) Depositar monto de la transferencia a
# (ChrGil 2022-01-11) la cuenta del beneficiario
class DepositAmount(DepositAmountRecived):
    def __init__(self, request_data: ResquestDataTransaccionRecibidaManual, beneficiario: GetInfoBeneficiario):
        self._request_data = request_data
        self._beneficiario = beneficiario
        self._deposit_amount()

    def _deposit_amount(self) -> NoReturn:
        cuenta.objects.deposit_amount(
            owner=self._beneficiario.beneficiario_info.get('id'),
            amount=self._request_data.get_monto
        )


# (ChrGil 2022-01-31) Calcula la comisión y retirar el dinero de la cuenta del cliente.
# (ChrGil 2022-01-31) La comisión negativa siempre se cobra de manera inmediata
class NegativeCommission:
    total: ClassVar[Decimal]

    def __init__(
            self,
            transaction_id: int,
            request_data: ResquestDataTransaccionRecibidaManual,
            comission: GetCommissionsFromPerson
    ):
        self._request_data = request_data
        self._transaction = transaction_id
        self._comission = comission
        self.total = self._calculate_comission
        self._create()
        self._withdraw_amount()

    @property
    def _calculate_comission(self) -> Decimal:
        comission = calculate_commission(
            amount=self._request_data.get_monto,
            comission=self._comission.info.get('commission_rel__percent'))

        total = add_iva(comission)
        return total

    def _create(self) -> NoReturn:
        Commission_detail.objects.create(
            comission=self._comission.info.get('id'),
            transaction=self._transaction,
            amount=self.total,
            status=1,
            payment_date=dt.datetime.now()
        )

    def _withdraw_amount(self) -> NoReturn:
        print(self._comission.beneficiario.beneficiario_info.get('id'))
        cuenta.objects.withdraw_amount(
            owner=self._comission.beneficiario.beneficiario_info.get('id'),
            amount=self.total
        )


# (ChrGil 2022-01-31) Calcula la comisión y la suma al monto de la cuenta del cliente
# (ChrGil 2022-01-31) y dependiendo de su serivico se cobrará a fin de mes
class PositiveCommission:
    total: ClassVar[Decimal]

    def __init__(
            self,
            transaction_id: int,
            request_data: ResquestDataTransaccionRecibidaManual,
            comission: GetCommissionsFromPerson
    ):
        self._request_data = request_data
        self._transaction = transaction_id
        self._comission = comission
        self.total = self._calculate_comission
        self._create()

    @property
    def _calculate_comission(self) -> Decimal:
        comission = calculate_commission(
            amount=self._request_data.get_monto,
            comission=self._comission.info.get('commission_rel__percent'))

        total = add_iva(comission)
        return total

    def _create(self) -> NoReturn:
        Commission_detail.objects.create(
            comission=self._comission.info.get('id'),
            transaction=self._transaction,
            amount=self.total,
            status=2,
            payment_date=None
        )


class CalculateCommission:
    total: ClassVar[Decimal]
    info_comission: ClassVar[Dict[str, Any]]

    def __init__(
            self,
            transaction_id: int,
            request_data: ResquestDataTransaccionRecibidaManual,
            comission: GetCommissionsFromPerson
    ):
        self.info_comission = comission.info

        # (ChrGil 2022-02-21) Si la cuenta eje madre no cuenta con el servicio de transferencias
        if not comission.info:
            raise ValueError("Tu producto actual no cuenta con el servicio de transferencias")

        # (ChrGil 2022-01-31) Comisión positiva
        if comission.info.get('commission_rel__type_id') == 1:
            _positive_commission = PositiveCommission(transaction_id, request_data, comission)
            self.total = _positive_commission.total

        # (ChrGil 2022-01-31) Comisión negativa
        if comission.info.get('commission_rel__type_id') == 2:
            _negative_comission = NegativeCommission(transaction_id, request_data, comission)
            self.total = _negative_comission.total


class SaveDetalleTransferencia:
    def __init__(self, request_data: Dict[str, Any], transaction_id: int):
        self.request_data = request_data
        self.transaction = transaction_id
        self._create()

    def _create(self) -> NoReturn:
        detalleTransferencia.objects.create(
            transfer_id=self.transaction,
            json_content=json.dumps(self.request_data),
        )


# (ChrGil 2022-01-24) Polipay Comission id: 7422 host de pruebas
# (ChrGil 2022-01-24) variable global RS_POLIPAY_COMISSION
class TransferComissionToPolipayComission:
    _rs_polipay_comission: ClassVar[int] = COST_CENTER_POLIPAY_COMISSION
    _info_polipay_comission: ClassVar[Dict[str, Union[int, str]]]
    _serializer_class: ClassVar[SerializerTransactionPolipayComission] = SerializerTransactionPolipayComission

    def __init__(
            self,
            request_data: ResquestDataTransaccionRecibidaManual,
            beneficiario: GetInfoBeneficiario,
            comission: CalculateCommission
    ):
        self._request_data = request_data
        self._emisor = beneficiario
        self._comission = comission
        self._amount_comission = round(float(comission.total), 4)
        self._get_info_polipay_comission()
        self._deposit_amount()

    def _get_info_polipay_comission(self) -> NoReturn:
        self._info_polipay_comission = cuenta.objects.get_info_polipay_comission(self._rs_polipay_comission)

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "comission_type": self._comission.info_comission.get('commission_rel__type_id'),
            "monto_actual": self._request_data.get_monto
        }

    @property
    def _data(self) -> Dict[str, Union[str, int, float]]:
        print(self._emisor.beneficiario_info)
        return {
            "empresa": "ND",
            "monto": self._amount_comission,
            "nombre_emisor": self._emisor.beneficiario_info.get('name'),
            "cuenta_emisor": self._emisor.beneficiario_account_info.get('cuentaclave'),
            "rfc_curp_emisor": self._emisor.beneficiario_info.get('rfc'),
            "nombre_beneficiario": self._info_polipay_comission.get('persona_cuenta__name'),
            "cta_beneficiario": self._info_polipay_comission.get('cuentaclave'),
            "rfc_curp_beneficiario": self._info_polipay_comission.get('persona_cuenta__rfc'),
            "cuentatransferencia_id": self._emisor.beneficiario_account_info.get('id'),
            "date_modify": self._request_data.get_fecha_operacion
        }

    def _create(self) -> NoReturn:
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()

    # (ChrGil 2022-02-01) Deposita el monto de la comisón a la cuenta de POLIPAY COMISSION
    def _deposit_amount(self) -> NoReturn:
        _type_comission = self._comission.info_comission.get('commission_rel__type_id')

        # (Positiva)
        if _type_comission == 1:
            ...

        # (Negativa)
        if _type_comission == 2:
            self._create()
            cuenta.objects.deposit_amount(self._rs_polipay_comission, self._amount_comission)


# (ChrGil 2022-01-11) Depositar monto de la transferencia a
# (ChrGil 2022-01-11) la cuenta del beneficiario
class DepositAmount(DepositAmountRecived):
    def __init__(self, request_data: ResquestDataTransaccionRecibidaManual, beneficiario: GetInfoBeneficiario):
        self._request_data = request_data
        self._beneficiario = beneficiario
        self._deposit_amount()

    def _deposit_amount(self) -> NoReturn:
        cuenta.objects.deposit_amount(
            owner=self._beneficiario.beneficiario_info.get('id'),
            amount=self._request_data.get_monto
        )


class SaldoRemanente:
    def __init__(self, transaction: transferencia):
        self._transaction = transaction
        self.saldo_remanente()

    @staticmethod
    def get_amount(account: str) -> Dict[str, Any]:
        return cuenta.objects.filter(
            Q(cuenta=account) | Q(cuentaclave=account)
        ).values('id', 'monto').first()

    def saldo_remanente(self):
        self._transaction.saldo_remanente_beneficiario += self.get_amount(self._transaction.cta_beneficiario).get(
            'monto')
        self._transaction.save()


class CreateTransactionReceived(viewsets.GenericViewSet):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Crear transacción recibida"]
    serializer_class = CreateTransactionReceivedIn
    # permission_classes = ()

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            cost_center_id = self.request.query_params['cost_center_id']

            with atomic():
                request_data = ResquestDataTransaccionRecibidaManual(request.data)
                beneficiario = GetInfoBeneficiario(cost_center_id)

                context = {
                    'cuenta_eje': beneficiario.beneficiario_info.get('name'),
                    'nombre_beneficiario': beneficiario.beneficiario_info.get('name'),
                    'cuenta_beneficiaria': beneficiario.beneficiario_account_info.get('id'),
                    "cuentaclave": beneficiario.beneficiario_account_info.get('cuentaclave'),
                    "cuenta_id": beneficiario.beneficiario_account_info.get('id'),
                    "monto": beneficiario.beneficiario_account_info.get('monto'),
                }

                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                transaction_instance = serializer.create()

                DepositAmount(request_data, beneficiario)
                SaldoRemanente(transaction_instance)
                SaveDetalleTransferencia(request.data, transaction_instance.id)
                comission_info = GetCommissionsFromPerson(beneficiario)
                comission = CalculateCommission(transaction_instance.id, request_data, comission_info)
                TransferComissionToPolipayComission(request_data, beneficiario, comission)

        except (ObjectDoesNotExist, ValueError, TypeError, IntegrityError, TypeError, DatabaseError) as e:
            err = MyHttpError(message="Ocurrio un error al depositar el saldo", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = {'code': 200, 'status': 'success','message': 'Tu operación se realizo de manera satisfactoria'}
            log.json_response(succ)
            return Response(succ, status=status.HTTP_200_OK)


class CreateTransactionReceivedFisicPerson(viewsets.GenericViewSet):
    serializer_class = SerializerCreateTransactionReceivedFisicPerson
    permission_classes = ()

    def create(self, request):
        log = RegisterLog(request.user, request)
        try:
            log.json_request(request.data)
            person_id = self.request.query_params['persona_fisica_id']

            request_data = ResquestDataTransaccionRecibidaManual(request.data)
            beneficiario = GetInfoBeneficiario(person_id)

            context = {
                'cuenta_eje': beneficiario.beneficiario_info.get('name'),
                'nombre_beneficiario': beneficiario.beneficiario_info.get('name'),
                'cuenta_beneficiaria': beneficiario.beneficiario_account_info.get('id'),
                "cuentaclave": beneficiario.beneficiario_account_info.get('cuentaclave'),
                "cuenta_id": beneficiario.beneficiario_account_info.get('id'),
                "monto": beneficiario.beneficiario_account_info.get('monto'),
            }

            serializer = self.serializer_class(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            transaction_instance = serializer.create()

            DepositAmount(request_data, beneficiario)
            SaldoRemanente(transaction_instance)
            SaveDetalleTransferencia(request.data, transaction_instance.id)
            comission_info = GetCommissionsFromPerson(beneficiario)
            comission = CalculateCommission(transaction_instance.id, request_data, comission_info)
            TransferComissionToPolipayComission(request_data, beneficiario, comission)

        except (ObjectDoesNotExist, ValueError, TypeError, IntegrityError, TypeError, DatabaseError) as e:
            err = MyHttpError(message="Ocurrio un error al depositar el saldo", real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = {'code': 200, 'status': 'success','message': 'Tu operación se realizo de manera satisfactoria'}
            log.json_response(succ)
            return Response(succ, status=status.HTTP_200_OK)
