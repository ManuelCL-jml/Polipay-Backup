import datetime as dt
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, ClassVar, NoReturn

from django.core.exceptions import ObjectDoesNotExist, FieldDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.exceptions import ValidationError

from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework import status

from MANAGEMENT.Standard.errors_responses import MyHttpError, ErrorResponseSTP
from MANAGEMENT.Standard.success_responses import MyHtppSuccess, SuccessResponseSTP
from apps.api_stp.client import CosumeConsultaSaldoCuentaAPISTP
from apps.api_stp.exc import StpmexException
from apps.api_stp.platform.any.serializers.serializers_stp import SerializerChangeStatus
from apps.api_stp.render_json import RenderJSONConsultaSaldoCuenta
from apps.api_stp.signature import SignatureAPIConsultaSaldoCuenta

from apps.logspolipay.manager import RegisterLog
from apps.users.models import cuenta


# (ChrGil 2021-11-30) Detallar transacciones pendinetes
class DetailPendingTransaction(UpdateAPIView):
    _data: ClassVar[dt.datetime] = dt.datetime.now()
    serializer_class = SerializerChangeStatus
    permission_classes = ()

    def update(self, request, *args, **kwargs):
        log = RegisterLog(0, request)

        try:
            fecha_consumo = self._data
            log.json_request(request.data)
            serializer = self.serializer_class(data=request.data, context={'log': log})
            serializer.is_valid(raise_exception=True)
            serializer.update_transfer(serializer.data, fecha_consumo)

        except MultiValueDictKeyError as e:
            message = "Asegúrese de haber ingresado todos los parametros"
            err = ErrorResponseSTP(message=message, code=400, real_error=str(e))
            log.json_response(err.error)
            return Response(err.error, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            message = "Ocurrió un error al momento de actualizar el estado de esta transferencia"
            err = ErrorResponseSTP(message=message, code=400, real_error=str(e))
            log.json_response(err.error)
            return Response(err.error, status=status.HTTP_400_BAD_REQUEST)

        else:
            succ = SuccessResponseSTP(message="Su operación se realizo de manera satisfactoria", code=200)
            log.json_response(succ.success)
            return Response(succ.success, status=status.HTTP_200_OK)


class APIConsultaSaldoCuenta:
    _api: ClassVar[CosumeConsultaSaldoCuentaAPISTP] = CosumeConsultaSaldoCuentaAPISTP
    _sing: ClassVar[SignatureAPIConsultaSaldoCuenta] = SignatureAPIConsultaSaldoCuenta
    _info_transaction: ClassVar[Dict[str, Any]]
    _demo: ClassVar[bool] = True
    _default_date: ClassVar[dt.date] = dt.date.today()

    def __init__(self, persona_cuenta: cuenta, demo: bool, empresa: str, **kwargs):
        self.persona_cuenta = persona_cuenta
        self.empresa = empresa
        self.fecha = kwargs.get("fecha", self._default_date.strftime("%Y%m%d"))
        self._demo_bool = demo
        self.cuentaclave = self._get_cuenta
        self._post()

    @property
    def _get_cuenta(self) -> str:
        return "646180171800000002"

    def _sing_data(self) -> SignatureAPIConsultaSaldoCuenta:
        return self._sing(persona_cuenta=self.cuentaclave, empresa=self.empresa)

    def _consulta_saldo_cuenta(self, data: SignatureAPIConsultaSaldoCuenta) -> Dict[str, Any]:
        print(data.json_data_consulta_pago)
        print(json.dumps(data.json_data_consulta_pago))
        return self._api(data.json_data_consulta_pago, demo_bool=self._demo).response

    def _post(self) -> NoReturn:
        try:
            # response = self._consulta_saldo_cuenta(self._sing_data())
            response = {
                "estado": 0,
                "mensaje": "Datos consultados correctamente",
                "respuesta":
                    {
                        "cargosPendientes": 1.23,
                        "saldo": 50.5
                    }
            }

            if response:
                self.response = response
        except StpmexException as e:
            err = MyHttpError(message=e.msg, real_error="STP Error", error_desc=e.desc)
            raise ValidationError(err.standard_error_responses())


class ComponentFondeoCuentaPersonaMoral:
    def __init__(self, fondeo: APIConsultaSaldoCuenta):
        self.fondeo = fondeo
        self.saldo_cuenta = fondeo.response.get('respuesta')
        self.update_account()

    def update_account(self):
        self.fondeo.persona_cuenta.saldo_fondeado_stp = self.saldo_cuenta.get("saldo")
        self.fondeo.persona_cuenta.cargos_pendientes_stp = self.saldo_cuenta.get("cargosPendientes")
        self.fondeo.persona_cuenta.hora_peticion_stp = dt.datetime.now() + dt.timedelta(minutes=30)
        self.fondeo.persona_cuenta.save()


class VerificaFondeoOrdenante:
    _api: ClassVar[APIConsultaSaldoCuenta] = APIConsultaSaldoCuenta

    def __init__(self, persona_cuenta: cuenta, transaction_info: Dict[str, Any], **kwargs):
        self.persona_cuenta = persona_cuenta
        self.transaction_info = transaction_info
        self.empresa = kwargs.get('empresa')

        if persona_cuenta.hora_peticion_stp:
            if persona_cuenta.hora_peticion_stp >= dt.datetime.now():
                fondeo = self._api(persona_cuenta, True, kwargs.get('empresa'))
                ComponentFondeoCuentaPersonaMoral(fondeo)

        if not persona_cuenta.saldo_fondeado_stp:
            fondeo = self._api(persona_cuenta, True, kwargs.get('empresa'))
            ComponentFondeoCuentaPersonaMoral(fondeo)

        self._verify_amount_stp()

    def _verify_amount_stp(self):
        if self.transaction_info.get('monto') > self.persona_cuenta.saldo_fondeado_stp:
            raise ValueError("No fue posible realizar la transacción, comuníquese con su ejecutivo Polipay")

# class ValidaSiTieneFondos:
#     def __init__(self, persona_cuenta: cuenta, demo: bool):
#         self.persona_cuenta = persona_cuenta
#         self._demo_bool = demo
#         self.info_account = self.hour_request_stp
#
#     @property
#     def hour_request_stp(self) -> Dict[str, Any]:
#         return cuenta.objects.filter(id=self.persona_cuenta.id).values(
#             "id",
#             "hora_peticion_stp"
#         ).first()
#
#     def two_request_limitation(self) -> Dict[str, Any]:
#         if self.info_account:
#             if self.info_account.get('hora_peticion_stp'):
