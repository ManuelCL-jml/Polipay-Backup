from django.db.models import Q
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import ListAPIView

from typing import Dict, List, Any, ClassVar, Union, NoReturn

import datetime as dt
from django.db.models import ObjectDoesNotExist
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.api_dynamic_token.api.web.views.views_dynamic_token import ValidateTokenDynamic
from apps.api_stp.client import CosumeAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.management import SetFolioOpetacionSTP
from apps.api_stp.signature import SignatureProductionAPIStpIndividual
from apps.contacts.models import contactos, HistoricoContactos
from apps.logspolipay.manager import RegisterLog
from apps.transaction.api.web.serializers.serializers_transaction_potpo import SerializerTransactioPolipayToPolipay
from apps.transaction.exc import ParamsRaiseException
from apps.users.models import cuenta, persona, grupoPersona
from apps.transaction.models import transferencia


class ComponentRequestData:
    def __init__(self, data: Dict[str, Any], params: Dict[str, Any]):
        self.data = data
        self.params = params

    @property
    def get_cost_center_id(self) -> int:
        return self.params.get('cost_center_id')

    @property
    def get_nombre_beneficiario(self) -> str:
        return self.data.get('nombre_beneficiario')

    @property
    def get_cta_beneficiario(self) -> str:
        return self.data.get('cta_beneficiario')

    @property
    def get_monto(self) -> str:
        return self.data.get('monto')

    @property
    def get_concepto_pago(self) -> str:
        return self.data.get('concepto_pago')

    @property
    def get_referencia_numerica(self) -> str:
        return self.data.get('referencia_numerica')

    @property
    def get_is_frecuent(self) -> bool:
        return self.data.get('is_frecuent')

    @property
    def get_alias(self) -> str:
        return self.data.get('alias')

    @property
    def get_token(self) -> str:
        return self.data.get('auth').get('token')


class ComponentBeneficiario:
    def __init__(self, request_data: ComponentRequestData):
        self.request_data = request_data
        info = self._info

        if info:
            self.info = info

        if not info:
            raise ValueError('No se encontro ningun beneficiario asociado a esa cuenta')

    @property
    def _info(self) -> Union[None, Dict[str, Any]]:
        return cuenta.objects.filter(is_active=True, persona_cuenta__state=True).filter(
            Q(cuenta=self.request_data.get_cta_beneficiario) |
            Q(cuentaclave=self.request_data.get_cta_beneficiario)
        ).values(
            'id',
            'monto',
            'cuentaclave',
            'persona_cuenta_id',
            'persona_cuenta__name',
            'persona_cuenta__rfc',
        ).first()


class ComponentEmisor:
    def __init__(self, request_data: ComponentRequestData):
        self.request_data = request_data
        info = self._info
        cuenta_eje_name = self.get_name_cuenta_eje(request_data.get_cost_center_id)

        if info:
            self.info = info

        if cuenta_eje_name:
            self.cuenta_eje_name = cuenta_eje_name

        if info is None:
            raise ValueError('No se encontro ningun emisor asociado a esa cuenta')

        if cuenta_eje_name is None:
            raise ValueError('Su cuenta no esta asociada a ninguna cuenta eje')

    @property
    def _info(self) -> Union[None, Dict[str, Any]]:
        return cuenta.objects.filter(
            is_active=True,
            persona_cuenta_id=self.request_data.get_cost_center_id,
            persona_cuenta__state=True
        ).values(
            'id',
            'monto',
            'cuentaclave',
            'persona_cuenta_id',
            'persona_cuenta__name',
            'persona_cuenta__rfc',
        ).first()

    @staticmethod
    def _cuenta_eje_centro_costos(cost_center_id: int) -> Union[None, Dict[str, Any]]:
        return grupoPersona.objects.filter(
            person_id=cost_center_id,
            relacion_grupo_id=5
        ).values('id', 'empresa_id', 'person_id', 'empresa__name', 'empresa__name_stp').first()

    @staticmethod
    def _cuenta_eje_cliente_externo(cliente_externo: int) -> Union[Dict[str, Any]]:
        return grupoPersona.objects.filter(
            person_id=cliente_externo,
            relacion_grupo_id=9
        ).values('id', 'empresa_id', 'person_id', 'empresa__name', 'empresa__name_stp').first()

    def get_name_cuenta_eje(self, cost_center_id: int) -> Union[None, str]:
        ceco = self._cuenta_eje_centro_costos(cost_center_id)

        if ceco:
            return ceco.get('empresa__name_stp')

        if not ceco:
            client = self._cuenta_eje_cliente_externo(cost_center_id)
            if not client:
                return None

            ceco = self._cuenta_eje_centro_costos(client.get('empresa_id'))
            if ceco:
                return ceco.get('empresa__name_stp')
        return None


class ComponentSaldoRemanente:
    def __init__(
            self,
            emisor: ComponentEmisor,
            beneficiario: ComponentBeneficiario,
            request_data: ComponentRequestData
    ):
        self.emisor = emisor
        self.beneficiario = beneficiario
        self.request_data = request_data

    @property
    def saldo_remanente_emisor(self) -> float:
        monto_actual = self.emisor.info.get("monto")
        monto_actual -= self.request_data.get_monto
        return monto_actual

    @property
    def saldo_remanente_beneficiario(self) -> float:
        monto_actual = self.beneficiario.info.get("monto")
        monto_actual += self.request_data.get_monto
        return monto_actual


class ComponentTransactionPolipayToPolipay:
    _serializer_class: ClassVar[SerializerTransactioPolipayToPolipay] = SerializerTransactioPolipayToPolipay

    def __init__(
            self,
            beneficiario: ComponentBeneficiario,
            emisor: ComponentEmisor,
            request_data: ComponentRequestData,
            created_to: persona,
            remanente: ComponentSaldoRemanente,
    ):
        self.beneficiario = beneficiario
        self.emisor = emisor
        self.request_data = request_data
        self.remanente = remanente
        self.person_id = created_to.get_only_id()
        self.transaction_id = self.create

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "cta_beneficiario": self.beneficiario.info.get('cuentaclave'),
            "monto": self.request_data.get_monto,
            "nombre_beneficiario": self.request_data.get_nombre_beneficiario,
            "concepto_pago": self.request_data.get_concepto_pago,
            "referencia_numerica": self.request_data.get_referencia_numerica,
        }

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "empresa": self.emisor.cuenta_eje_name,
            "monto": self.emisor.info.get('monto'),
            "cuenta_emisor": self.emisor.info.get('cuentaclave'),
            "nombre_emisor": self.emisor.info.get('persona_cuenta__name'),
            "rfc_curp_emisor": self.emisor.info.get('persona_cuenta__rfc'),
            "rfc_curp_beneficiario": self.beneficiario.info.get('persona_cuenta__rfc'),
            "created_to": self.person_id,
            "saldo_remanente_emisor": self.remanente.saldo_remanente_emisor,
            "cuentatransferencia_id": self.emisor.info.get('id'),
        }

    @property
    def create(self) -> int:
        serialzer = self._serializer_class(data=self._data, context=self._context)
        serialzer.is_valid(raise_exception=True)
        instance = serialzer.create()
        return instance.get_only_id_transfer


class ComponentTransactionInfo:
    def __init__(self, transaction: ComponentTransactionPolipayToPolipay):
        self.transaction = transaction.transaction_id
        self.transaction_info = self._get_info_transaction

    @property
    def _get_info_transaction(self) -> Dict[str, Any]:
        return transferencia.objects.select_related(
            'masivo_trans',
            'transmitter_bank',
            'receiving_bank'
        ).filter(
            id=self.transaction
        ).values(
            'id',
            'clave_rastreo',
            'concepto_pago',
            'cta_beneficiario',
            'cuenta_emisor',
            'empresa',
            'monto',
            'nombre_beneficiario',
            'nombre_emisor',
            'referencia_numerica',
            'rfc_curp_beneficiario',
            't_ctaBeneficiario',
            't_ctaEmisor',
            'rfc_curp_emisor',
            'tipo_pago',
            'cuentatransferencia__persona_cuenta__rfc'
        ).first()


class ComponenWithdrawEmisor:
    def __init__(self, transaction: ComponentTransactionInfo, emisor: ComponentEmisor):
        self.transaction = transaction.transaction_info
        self.emisor_id = emisor.info.get('id')
        self._withdraw()

    def _withdraw(self):
        try:
            cuenta_emisor: cuenta = cuenta.objects.get(id=self.emisor_id)
            cuenta_emisor.monto -= self.transaction.get('monto')
            cuenta_emisor.save()
        except ObjectDoesNotExist as e:
            message = "Ocurrio un error al retirar el dinero de su cuenta"
            err = MyHttpError(message=message, real_error=str(e))
            raise ValidationError(err.standard_error_responses())


class ComponenCosumeAPIStpRegistraOrden:
    _sing: ClassVar[SignatureProductionAPIStpIndividual] = SignatureProductionAPIStpIndividual
    _folio_operacion: ClassVar[SetFolioOpetacionSTP] = SetFolioOpetacionSTP
    _api: ClassVar[CosumeAPISTP] = CosumeAPISTP

    def __init__(self, transaction: ComponentTransactionInfo, demo_bool: bool):
        self._transaction = transaction.transaction_info
        self._demo_bool = demo_bool
        self._registra_orden()

    def _sing_json(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        return self._sing(transaction).json_data_registra_orden

    def _registra_orden(self) -> NoReturn:
        data = self._sing_json(self._transaction)
        api = self._api(data, demo_bool=self._demo_bool)
        self._folio_operacion(api.response, data.get('claveRastreo'))


class CreateContact:
    def __init__(self, request_data: ComponentRequestData, emisor: ComponentEmisor):
        self._request_data = request_data
        self._emisor = emisor

        contacto = contactos.objects.filter(person_id=self._emisor.info.get('persona_cuenta_id'),
                                            cuenta=self._request_data.get_cta_beneficiario, tipo_contacto_id=2)

        if request_data.get_is_frecuent:
            if contacto:
                err = MyHttpError('Ya existe un contacto frecuente registrado con esta cuenta', real_error=None)
                raise ValidationError(err.standard_error_responses())

            if request_data.get_alias is None:
                err = MyHttpError('Debes de definir un alias', real_error=None)
                raise ValidationError(err.standard_error_responses())

            self._create()
            self._create_historico_contacto()

    def _create(self) -> NoReturn:
        contactos.objects.create_contact(
            clabe=self._request_data.get_cta_beneficiario,
            alias=self._request_data.get_alias,
            nombre=self._request_data.get_nombre_beneficiario,
            banco_id=86,
            persona_id=self._emisor.info.get('persona_cuenta_id'),
            email=None,
            rfc_beneficiario=None,
            tipo_contacto_id=1
        )

    def _create_historico_contacto(self) -> NoReturn:
        contacto = contactos.objects.last()
        HistoricoContactos.objects.create(
            fechaRegistro=dt.datetime.now(),
            contactoRel_id=contacto.id,
            operacion_id=1,
            usuario_id=self._emisor.info.get('persona_cuenta_id')
        )


class CreateTransactionPolipayToPolipayV2(GenericViewSet):
    _request_data: ClassVar[ComponentRequestData] = ComponentRequestData
    _beneficiario_class: ClassVar[ComponentBeneficiario] = ComponentBeneficiario
    _emisor_class: ClassVar[ComponentEmisor] = ComponentEmisor
    _create_transaction: ClassVar[ComponentTransactionPolipayToPolipay] = ComponentTransactionPolipayToPolipay
    _registra_orden: ClassVar[ComponenCosumeAPIStpRegistraOrden] = ComponenCosumeAPIStpRegistraOrden
    _transaction_info: ClassVar[ComponentTransactionInfo] = ComponentTransactionInfo
    _dynamic_token: ClassVar[ValidateTokenDynamic] = ValidateTokenDynamic
    _withdraw_amount: ClassVar[ComponenWithdrawEmisor] = ComponenWithdrawEmisor
    _create_contact: ClassVar[CreateContact] = CreateContact
    _saldo_remanente: ClassVar[ComponentSaldoRemanente] = ComponentSaldoRemanente

    def create(self, request):
        user: persona = request.user
        log = RegisterLog(user, request)
        log.json_request(request.data)

        try:
            with atomic():
                request_data = self._request_data(request.data, self.request.query_params.copy())
                self._dynamic_token(request_data.get_token, user)
                beneficiario = self._beneficiario_class(request_data)
                emisor = self._emisor_class(request_data)

                remanente = self._saldo_remanente(emisor, beneficiario, request_data)
                transaction = self._create_transaction(beneficiario, emisor, request_data, user, remanente)
                transaction_info = self._transaction_info(transaction)
                self._withdraw_amount(transaction_info, emisor)
                self._registra_orden(transaction_info, demo_bool=True)
                self._create_contact(request_data, emisor)

        except ObjectDoesNotExist as e:
            message = "No fue posible retirar el dinero de su cuenta"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_404_NOT_FOUND)

        except (IndexError, ValueError, IndexError, TypeError) as e:
            message = "Ocurrió un error al realizar el movimiento"
            err = MyHttpError(message=message, real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        except StpmexException as e:
            err = MyHttpError(message=e.msg, real_error="STP Error", error_desc=e.desc)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            message = "Transacción exitosa. La operación está en proceso, por favor espere un momento."
            succ = MyHtppSuccess(message=message)
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)
        finally:
            err = MyHttpError(message="finally", real_error="finally")
            log.json_response(err.standard_error_responses())


class ComponentListTransactionPolipayToPolipayStatus:
    _default_size: ClassVar[int] = 100

    def __init__(self, **kwargs):
        self.status_id = kwargs.get('status_id')
        self.cost_center_id = kwargs.get('cost_center_id')
        self.size = kwargs.get('size', self._default_size)
        self.end_date = kwargs.get('end_date', dt.datetime.now())
        self.start_date = kwargs.get('start_date', dt.datetime.now() - dt.timedelta(days=91))
        self.nombre_beneficiario = kwargs.get('nombre_beneficiario', '')
        self.list = self._list

    @property
    def get_account_emisor(self) -> Dict[str, Any]:
        return cuenta.objects.filter(persona_cuenta_id=self.cost_center_id).values(
            "id",
            "cuentaclave"
        ).first()

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return transferencia.objects.filter(
            Q(date_modify__date__gte=self.start_date) &
            Q(date_modify__date__lte=self.end_date)
        ).filter(
            cuenta_emisor__icontains=self.get_account_emisor.get('cuentaclave'),
            status_trans_id=self.status_id,
            tipo_pago_id=1,
            nombre_beneficiario__icontains=self.nombre_beneficiario
        ).values(
            "id",
            "nombre_beneficiario",
            "monto",
            "clave_rastreo",
            "date_modify"
        ).order_by('-date_modify')


class ListTransactionPolipayToPolipayStatus(ListAPIView):
    _list: ClassVar[ComponentListTransactionPolipayToPolipayStatus] = ComponentListTransactionPolipayToPolipayStatus
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            list_transaction = self._list(**data)
            self.pagination_class.page_size = list_transaction.size
        except ParamsRaiseException as e:
            err = MyHttpError('Ocurrio un error al listar los movimientos', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.get_paginated_response(self.paginate_queryset(list_transaction.list))
