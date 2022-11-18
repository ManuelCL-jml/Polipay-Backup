from typing import Dict, ClassVar, List, Any

from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import status

from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.commissions.api.web.serializers.serializers_comission import SerializerUpdateProductsServices
from apps.logspolipay.manager import RegisterLog
from apps.users.exc import UserAdminException
from apps.users.models import persona
from apps.commissions.api.web.components.components_comission import ComponentListPositiveComission, \
    ComponentInfoComission, ComponentInfoCuentaEje, ComponentDetailServiceComission

from MANAGEMENT.Standard.errors_responses import MyHttpError


# comissions/web/v3/LiscomPos/list/
class ListComissionPositive(ListAPIView):
    # permission_classes = ()
    pagination_class = PageNumberPagination

    # PARAMS: cost_center_id, start_date, end_date, size
    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:

            admin: persona = request.user
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            info = ComponentInfoComission(admin, **data)
            comission = ComponentListPositiveComission(cost_center_account_id=info.account_id, **data)

        except ValueError as e:
            err = MyHttpError(message="Ocurrio un error al listar las comisiones", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            self.pagination_class.page_size = comission.size
            return self.get_paginated_response(self.paginate_queryset(comission.comission_list))


# comissions/web/v3/DetComPos/list/
class DetailComissionPositive(RetrieveAPIView):
    # permission_classes = ()

    # PARAMS: comission_id
    def retrieve(self, request, *args, **kwargs):
        try:
            admin: persona = request.user
            # admin: persona = persona.objects.get(id=63)
            comission_id: int = self.request.query_params['comission_id']

            ComponentInfoComission(admin, comission_id=comission_id)
            comission = ComponentListPositiveComission(comission_id=comission_id)
        except ValueError as e:
            err = MyHttpError(message="Ocurrio un error al listar las comisiones", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(comission.comission_detail, status=status.HTTP_200_OK)


class DetailComissionCompany(RetrieveAPIView):
    _cuenta_eje_info: ClassVar[ComponentInfoCuentaEje] = ComponentInfoCuentaEje
    _detail: ClassVar[ComponentDetailServiceComission] = ComponentDetailServiceComission
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        try:
            cuenta_eje_id: int = self.request.query_params["cuenta_eje_id"]
            info = self._cuenta_eje_info(cuenta_eje_id)
            detail = self._detail(cuenta_eje_id)

        except ValueError as e:
            err = MyHttpError(message="No fue posible mostrar los detalles de los servicios", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "CuentaEje": info.cuenta_eje,
                "Services": detail.list
            }, status=status.HTTP_200_OK)


class RequestDataEditComission:
    def __init__(self, request_data: Dict[str, Any], params: Dict[str, Any]):
        self.request_data = request_data
        self.params = params

    @property
    def get_cuenta_eje_id(self) -> int:
        return self.params.get("cuenta_eje_id")

    @property
    def get_comission_list(self) -> List[Dict[str, Any]]:
        return self.request_data.get("ComissionList")


class ComponentRazonSocial:
    def __init__(self, request_data: RequestDataEditComission):
        self._check_cuenta_eje(request_data.get_cuenta_eje_id)

    @staticmethod
    def _check_cuenta_eje(cuenta_eje_id: int):
        if not persona.objects.filter(id=cuenta_eje_id, state=True, is_active=True).exists():
            raise ValueError("Recurso no encontrado")


class ComponentUpdateComission:
    _serializer_class: ClassVar[SerializerUpdateProductsServices] = SerializerUpdateProductsServices

    def __init__(self, request_data: RequestDataEditComission, user: persona):
        self.is_superuser = user.is_superuser

        if len(request_data.get_comission_list) > 0:
            self.update(request_data.get_comission_list)

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "is_superuser": self.is_superuser
        }

    @staticmethod
    def _data(**kwargs) -> Dict[str, Any]:
        return {
            "id": kwargs.get("CommissionId"),
            "percent": kwargs.get("Percent"),
            "amount": kwargs.get("Amount"),
            "type_id": kwargs.get("TypeId"),
            "service_id": kwargs.get("ServiceId"),
        }

    def update(self, request_data: List[Dict[str, Any]]):
        for row in request_data:
            serializer = self._serializer_class(data=self._data(**row), context=self._context)
            serializer.is_valid(raise_exception=True)
            serializer.update()


class UpdateComission(UpdateAPIView):
    _request_data: ClassVar[RequestDataEditComission] = RequestDataEditComission
    _cuenta_eje: ClassVar[ComponentRazonSocial] = ComponentRazonSocial
    _update: ClassVar[ComponentUpdateComission] = ComponentUpdateComission
    _log: ClassVar[RegisterLog] = RegisterLog

    def update(self, request, *args, **kwargs):
        user: persona = request.user
        log = self._log(user, request)
        log.json_request(request.data)
        try:
            with atomic():
                request_data = self._request_data(request.data, self.request.query_params.copy())
                self._cuenta_eje(request_data)
                self._update(request_data, user)
        except (KeyError, ValueError, TypeError) as e:
            err = MyHttpError(message=str(e), real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        except UserAdminException as e:
            err = MyHttpError(message=e.message, real_error=e.message)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            scc = MyHtppSuccess(message="La operación se realizó de manera exitosa")
            log.json_response(scc.standard_success_responses())
            return Response(scc.standard_success_responses(), status=status.HTTP_200_OK)
