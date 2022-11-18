import mimetypes
from datetime import datetime
import json
from typing import Any

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status, viewsets, pagination
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import logout
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView

from django.http.response import FileResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.permision.manager import *
from apps.users.api.web.admin.serializers.serializer_admin import *
from apps.users.management import get_information_client, get_Object_orList_error
from apps.users.messages import send_mail_superuser
from apps.users.models import persona, ConcentradosAuxiliar
from apps.users.management import filter_ext_client, ext_client, sol_ext_client
from polipaynewConfig import settings
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info


class RequestDataAdmin:
    def __init__(self, request_data: Dict[str, Any]):
        self._request_data = request_data

    @property
    def is_superuser(self) -> bool:
        return self._request_data.get('is_superuser')

    @property
    def is_staff(self) -> bool:
        return self._request_data.get('is_staff')


class ToAssingPermissionAdmin:
    def __init__(self, request_data: RequestDataAdmin, admin: persona):
        if request_data.is_superuser is True and request_data.is_staff is True:
            SuperAdminAddGroup(admin)

        if request_data.is_superuser is True and request_data.is_staff is False:
            SuperAdminAddGroup(admin)

        if request_data.is_superuser is False and request_data.is_staff is True:
            SuperAdminAddGroup(admin)

        if request_data.is_superuser is False and request_data.is_staff is False:
            raise ValueError('Debe seleccionar una opción')


class AdminGenericViewSet(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear Administrador", "Ver Administradores", "Editar Administrador", "Eliminar Administrador"]
    serializer_class = CreateAdminSerializerIn
    message_response = 'Tu operación se realizó satisfactoriamente.'

    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(persona, *args, **kwargs)

    def get(self):
        admin = self.get_queryset(id=self.request.query_params['id'])
        serializer = CreateAdminSerializerOut(instance=admin)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        try:
            with atomic():
                request_data = RequestDataAdmin(request.data)
                context = {'ip': get_information_client(request), 'method': request.method, 'super_admin': request.user, 'log': log}
                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                instance = serializer.create()
                ToAssingPermissionAdmin(request_data, instance)
                send_mail_superuser(instance, serializer.data['password'])
        except ValueError as e:
            res = {'status': "Ocurrió un error al momento de dar de alta un administrador"}
            log.json_response(res)
            return Response(res, status=status.HTTP_201_CREATED)

        succ = {'status': self.message_response}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_201_CREATED)

    def put(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)

        admin = self.get_queryset(email=request.data['id'])
        context = {'method': request.method, 'super_admin': request.user, 'instance': admin}
        serializer = self.serializer_class(data=request.data, instance=admin, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.update(admin)

        succ = {'status': self.message_response}
        log.json_response(succ)

        return Response(succ, status=status.HTTP_200_OK)

    def delete(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        admin = self.get_queryset(email=request.data['email'])
        context = {'super_admin': request.user, 'log': log}
        serializer = DeleteAdminSerializerIn(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.update(admin)

        succ = {'status': self.message_response}
        log.json_response(succ)
        return Response(succ, status=status.HTTP_200_OK)


class ListContrados(GenericViewSet):
    serializer_class    = ConcentradosIN
    permission_classes = [IsAuthenticated]
    #permission_classes  = ()

    @method_decorator(cache_page(60 * 0.1))
    def get(self, request):
        # ingresos = settings.TINGRESOSC
        # egresos = settings.TEGRESOSC
        # settings.TINGRESOSC = 0
        # settings.TEGRESOSC = 0
        # listaResponse = {'ingresos': ingresos, 'egresos': egresos}
        # succ = MyHtppSuccess(message="tu operacion se realizo satisfactoriamente", extra_data=listaResponse)
        # return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)
        log = RegisterLog(request.user, request)
        log.json_request(request.query_params)
        pk = self.request.query_params["persona"]
        queryExistePersona = persona.objects.filter(id=pk).exists()
        if queryExistePersona:
            queryTotales = ConcentradosAuxiliar.objects.filter(persona_id=pk).values("json_content").first()
            if queryTotales:
                # objJson         = json.loads( str(queryTotales[0]["json_content"]).replace("'","\"") )
                objJson = json.loads(queryTotales.get("json_content"))
                r = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "field": "totales",
                            "data": objJson,
                            "message": "Totales recuperados correctamente."
                        }
                    ]
                }
                log.json_response(r)
                return Response(r, status=status.HTTP_200_OK)
            else:
                r = {
                    "code": [400],
                    "status": "ERROR",
                    "detail": [
                        {
                            "field": "totales",
                            "data": None,
                            "message": "No existe registro de Totales."
                        }
                    ]
                }
                log.json_response(r)
                return Response(r, status=status.HTTP_200_OK)

        else:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "persona",
                        "data": pk,
                        "message": "Persona no existe."
                    }
                ]
            }
            log.json_response(r)
            return Response(r, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        log = RegisterLog(request.user, request)
        log.json_request(request.data)
        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.getQuery(serializer.validated_data)
        else:
            err = MyHttpError(message="revisar datos enviados", real_error=serializer.errors)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        if request.data["archivo"] == True:
            filename = 'TMP/web/Estado_Cuentas/Excel/Reporte-Concentrado.xlsx'
            filepath = filename
            # path = open(filepath, 'r')
            mime_type, _ = mimetypes.guess_type(filepath)
            response = FileResponse(open(filename, 'rb'))
            response['Content-Disposition'] = "attachment; filename=%s" % filename
            return response
        page = self.paginate_queryset(data)
        serializer = ConcentradosOUT(page, many=True)

        from datetime import datetime
        totalIngresos = 0
        totalEgresos = 0
        for elemento in serializer.data:
            if elemento["monto"] < 0:
                totalEgresos += elemento["monto"]
            else:
                totalIngresos += elemento["monto"]

        queryExisteRegPersona   = ConcentradosAuxiliar.objects.filter(persona_id=request.data["persona"]).exists()
        if queryExisteRegPersona:
            instancia = get_Object_orList_error(ConcentradosAuxiliar, persona_id=request.data["persona"])
            instancia.creation_date = datetime.now()
            json_content = {"total_ingresos": totalIngresos, "total_egresos": totalEgresos}
            instancia.json_content = json.dumps(json_content)
            instancia.save()
        else:
            json_content = {"total_ingresos": totalIngresos, "total_egresos": totalEgresos}
            ConcentradosAuxiliar(
                creation_date=datetime.now(),
                json_content=json.dumps(json_content),
                persona_id=request.data["persona"]
            ).save()
        log.json_response(serializer.data)
        return self.get_paginated_response(serializer.data)


class DashboardAdmin(ListAPIView):
    #permission_classes = (BlocklistPermissionV2,)
    #permisos = ["Crear Administrador", "Ver Administradores", "Editar Administrador", "Eliminar Administrador"]
    serializer_class    = SerializerDashboardAdmin
    permission_classes  = [IsAuthenticated]

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request):
        log = RegisterLog(request.user, request)
        pk      = self.request.query_params["centro_costo"]
        log.json_request(request.query_params)
        r       = {}
        objJson = {}

        context = {
            'request': request,
            'log': log
        }

        serializer  = self.serializer_class(data=self.request.query_params, context=context)
        if serializer.is_valid(raise_exception=True):
            objJson = serializer.getTransactionSummary(serializer.validated_data)

            r   = {
                "code":[200],
                "status":"OK",
                "detail":[
                    {
                        "field":None,
                        "data":objJson,
                        "message":"Resumen de movimientos."
                    }
                ]
            }
        log.json_response(r)
        return Response(r, status=status.HTTP_200_OK)


# (ManuelCalixtro 17/02/2022) Se creo endpoint que lista los administradores polipay
class ListPolipayAdmins(ListAPIView):

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size
        email= self.request.query_params['email']
        name = self.request.query_params['name']

        log.json_request(request.query_params)

        polipay_admins = persona.objects.filter_admins_polipay(name, email)

        page = self.paginate_queryset(polipay_admins)
        return self.get_paginated_response(page)

