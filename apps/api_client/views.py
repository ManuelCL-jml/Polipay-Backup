import datetime
import time
import threading
import dateutil.parser

from dataclasses import dataclass
from django.shortcuts import render
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from typing import Optional

from apps.users.models import grupoPersona, persona, tarjeta
from apps.solicitudes.models import Solicitudes
from apps.transaction.models import transferencia, TransMasivaProg
from apps.users.models import cuenta
from .management import *
from .serializers import *
from .messages import *
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from MANAGEMENT.notifications.movil.notifyAppUser import notifyAppUser
from MANAGEMENT.EndPoint.EndPointInfo import get_info

from .manager import *
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from .models import *
from .inntecFunctions import listCard
from django.db import transaction
from polipaynewConfig.exceptions import MensajeError

"""
    Crear una solicitud para el servicio API
"""


class CreateAPIRequest(viewsets.GenericViewSet):
    serializer_class = SerializerAPIRequestIn
    queryset = ()
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def create(self, request):
        endpoint = get_info(request)
        id_cuenta_eje = get_id_cuenta_eje(request.data["id_admin_cuenta_eje"],endpoint)

        RegisterSystemLog(idPersona=request.data["id_admin_cuenta_eje"], type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)

        existing_request = Solicitudes.objects.filter(Q(estado_id=1) | Q(estado_id=4),
                                                      personaSolicitud_id=id_cuenta_eje,
                                                      tipoSolicitud_id=8)
        if existing_request:
            message_already_created = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": id_cuenta_eje,
                        "field": "personaSolicitud_id",
                        "message": "API request already Created or Accepted",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_admin_cuenta_eje"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_already_created)
            return Response(message_already_created, status=status.HTTP_400_BAD_REQUEST)
        else:
            context = {
                'cuenta_eje': id_cuenta_eje,
                'tipo_solicitud': 8,
                'nombre': 'Credencial API Dispersa',
            }
            serializer = self.serializer_class(data=request.data, context=context)
            if serializer.is_valid(raise_exception=True):
                serializer.create()
                send_mail_superuser(id_cuenta_eje)

                message_request_succesfull = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "data": "",
                            "field": "",
                            "message": "Request successfully sended",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=request.data["id_admin_cuenta_eje"], type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_request_succesfull)
                return Response(message_request_succesfull, status=status.HTTP_201_CREATED)


"""
    Listar todas las solicitudes en espera 
"""


class ListAPIRequest(viewsets.GenericViewSet):
    serializer_class = SerializerListAPIRequest
    queryset = ()
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request):
        endpoint = get_info(request)
        #endpoint = "http://127.0.0.1:8000/api_client/v1/APIReqList/list/"
        validate_superadmin(request.data["id_superadmin"], endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)

        queryset = Solicitudes.objects.filter(tipoSolicitud_id=8, estado_id=1).order_by("fechaSolicitud")
        if not queryset:
            message_no_requests = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Zero API requests pending",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_no_requests)
            return Response(message_no_requests, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = SerializerListAPIRequest(queryset, many=True)
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Aceptar/Rechazar la solicitud del servicio API y notificar
    *En caso de ser aceptada se crean credenciales
"""


class ChangeRequestStatus(viewsets.GenericViewSet):
    serializer_class = SerializerChangeRequestStatus
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    # AQUI DEBO RECIBIR ANTES EL CAMBIO DE ESTADO QUE REALIZA BENITO, Y ENTONCES VOY SOLICITUD POR SOLICITUD VIENDO EL VALOR ASIGNADO A SU ESTADO

    def create(self, request):
        endpoint = get_info(request)
        validate_superadmin(request.data["id_superadmin"], endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint= endpoint,
                          objJsonRequest=request.data)

        try:
            existing_request = Solicitudes.objects.get(id=request.data["id_solicitud"], estado_id=1,
                                                       personaSolicitud_id=request.data["id_cuenta_eje"],
                                                       tipoSolicitud_id=8)
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id_solicitud"],
                        "field": "id",
                        "message": "API request not found",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_found)
            raise ValidationError(message_not_found)
        if request.data["estado_id"] == 4:
            # SI RECIBO QUE EL ESTADO DE LA SOLICITUD ES ACEPTAR ENTONCES CAMBIÓ A 4 EN LA DB
            serializer = SerializerChangeRequestStatus(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(existing_request)
                CredencialesAPI.objects.create_credentials(request.data["id_cuenta_eje"])
                # AQUI YA VAN LAS CREDENCIALES Y DEPUÉS EL ENVÍO DE CORREO
                send_acceptance_mail_admin(request.data["id_cuenta_eje"])
                message_acceptance = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "data": "",
                            "field": "",
                            "message": "Request Status accepted successfully",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_acceptance)
                return Response(message_acceptance, status=status.HTTP_201_CREATED)
            # ENTONCES MANDO LLAMAR METODO PARA CREAR CRDENCIALES
            # ENVIO CORREO CON CREDENCIALES (admin_APIresponseA_U.html)

        elif request.data["estado_id"] == 8:  # Estado rechazado
            serializer = SerializerChangeRequestStatus(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(existing_request)
                send_reject_mail_admin(request.data["id_cuenta_eje"])
                message_reject = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "data": "",
                            "field": "",
                            "message": "Request Status rejected successfully",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_reject)
                return Response(message_reject, status=status.HTTP_200_OK)
            # NOTIFICO CON CORREO AL ADMINISTRATIVO SOBRE LA DECISIÓN (admin_APIresponseD.html)
        else:
            message_invalid_status = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["estado_id"],
                        "field": "estado_id",
                        "message": "Invalid status",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_invalid_status)
            return Response(message_invalid_status, status=status.HTTP_400_BAD_REQUEST)


"""
    Listar todas las credenciales activas 
"""


class ListAPICredentials(viewsets.GenericViewSet):
    serializer_class = SerializerListAPICredentials
    queryset = ()
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request):
        # SE DEBE VALIDAR QUE EL ÚNICO QUE PUEDE SOLICITAR VER LAS CREDENCIALES DE LOS CLIENTES SEA EL SUPER ADMIN DEL SISTEMA
        endpoint = get_info(request)
        validate_superadmin(request.data["id_superadmin"], endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint=endpoint,
                          objJsonRequest = request.data)

        queryset = CredencialesAPI.objects.filter(is_active=1).order_by("fechaCreacion")
        if not queryset:
            message_no_credentials = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Zero API active credentials",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_no_credentials)
            return Response(message_no_credentials, status=status.HTTP_400_BAD_REQUEST)
        else:

            serializer = SerializerListAPICredentials(queryset, many=True)
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Listado de credenciales por filtro de nombre de la cuenta eje y/o rango de fechas de creación
"""


class FilterAPICredentials(viewsets.GenericViewSet):
    serializer_class = SerializerFilterAPICredentials
    queryset = ()
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request):
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        endpoint = get_info(request)
        id_superadmin = request.data["id_superadmin"]
        validate_superadmin(id_superadmin,endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint=endpoint,
                          objJsonRequest=log_dict)

        # SE DEBE VALIDAR QUE EL ÚNICO QUE PUEDE SOLICITAR VER LAS CREDENCIALES DE LOS CLIENTES SEA EL SUPER ADMIN DEL SISTEMA

        name = request.query_params['name']
        date_start = request.query_params['date_start']
        date_end = request.query_params['date_end']
        if not date_start:
            date_start = datetime.date(2000, 12, 31)
        if not date_end:
            date_end = str(datetime.date.today())
        if name == 'null':
            name = ''

        queryset = filter_credentials(name, date_start, date_end)
        if not queryset:
            message_no_credentials = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Zero API active credentials",
                    }
                ]
            }

            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_no_credentials)
            return Response(message_no_credentials, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = SerializerFilterAPICredentials(queryset, many=True)
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Bloqueo de credenciales seleccionadas por cuenta eje
"""


class BlockApiCredentials(UpdateAPIView):
    serializer_class = SerializerChangeRequestStatus
    queryset = ()
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def update(self, request):
        endpoint = get_info(request)
        validate_superadmin(request.data["id_superadmin"], endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)

        try:
            existing_request = Solicitudes.objects.get(id=request.data["id_solicitud"], estado_id=4,
                                                       personaSolicitud_id=request.data["id_cuenta_eje"],
                                                       tipoSolicitud_id=8)
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id_solicitud"],
                        "field": "id",
                        "message": "API request not found",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_found)
            raise ValidationError(message_not_found)
        if request.data["estado_id"] == 9:  # Estado Bloqueado
            serializer = SerializerChangeRequestStatus(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(existing_request)
                try:
                    existing_credencial = CredencialesAPI.objects.get(personaRel_id=request.data["id_cuenta_eje"])
                except Exception as e:
                    message_not_found_credential = {
                        "code": [400],
                        "status": "ERROR",
                        "detail": [
                            {
                                "data": request.data["id_cuenta_eje"],
                                "field": "personaRel_id",
                                "message": "Cuenta eje has no API credentials",
                            }
                        ]
                    }
                    RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                                      endpoint=endpoint,
                                      objJsonResponse=message_not_found_credential)
                    raise ValidationError(message_not_found_credential)
                existing_credencial.delete()
                send_block_mail_admin(request.data["id_cuenta_eje"])
                message_blocked = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "data": "",
                            "field": "",
                            "message": "API Credential blocked successfully",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_blocked)
                return Response(message_blocked, status=status.HTTP_201_CREATED)
        else:
            message_invalid_status = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["estado_id"],
                        "field": "estado_id",
                        "message": "Invalid status",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_invalid_status)
            return Response(message_invalid_status, status=status.HTTP_400_BAD_REQUEST)


"""
    Actualización y reenvío de credenciales por cuenta eje
"""


class ResendCredential(UpdateAPIView):
    serializer_class = SerializerUpdateCredentials
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def update(self, request):
        endpoint = get_info(request)
        validate_superadmin(request.data["id_superadmin"], endpoint)
        RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)

        try:
            existing_credential = CredencialesAPI.objects.get(personaRel_id=request.data["id_cuenta_eje"])
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["id_cuenta_eje"],
                        "field": "personaRel_id",
                        "message": "API Credential not found",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_found)
            raise ValidationError(message_not_found)

        serializer = SerializerUpdateCredentials(data=request.data)
        if serializer.is_valid(raise_exception=True):
            username, password = CredencialesAPI.objects.create_username_password(request.data["id_cuenta_eje"])
            serializer.update(existing_credential, username, password)
            resend_credentials_mail(request.data["id_cuenta_eje"])
            message_new_credentials = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "New Credentials successfully created",
                    }
                ]
            }
            RegisterSystemLog(idPersona=request.data["id_superadmin"], type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_new_credentials)
            return Response(message_new_credentials, status=status.HTTP_201_CREATED)


"""
    Ver numero de tarjetas en stock por cuenta eje
    
    NOTA: Este código busca tarjetas por cuenta eje asignadas en la tabla "users_tarjeta" verificando que pertenezacn
    al id indicado en el campo "clave_empleado", sin embargo ese campo ya fue corregido y ahora es "clientePrincipal_id".
    Este cambio solo fue implementado en DB de pruebas, aún no se corrige en produccion por lo que la vista actual debe
    variar dependiendo el entorno de ejecucion (pruebas/producción) 
    
    NOTA2: Por el momento debido a fallas en el entorno de pruebas inntec no se puede realizar la actualización a "estado =2"
    que corresponde a una tarjeta asignada, por lo que todas las tarjetas de la CE solicitada aparecerán como disponibles 
    por el moemnto, en cuanto inntec indique que ya liberó el error la actualñización se ejecutará
"""


class CuentaEjeCardStock(viewsets.GenericViewSet):
    serializer_class = SerializerCardStock
    permission_classes = ()

    # permission_classes = [IsAuthenticated]
    def list(self, request, *args, **kwargs):
        endpoint = get_info(request)
        credentials_cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        card_stock = get_card_Stock(credentials_cuenta_eje_id)
        serializer = SerializerCardStock(data=card_stock)
        if serializer.is_valid(raise_exception=True):
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Listar detalles del personal externo de una cuenta eje recibiendo el id del administrativo de la CE
    
"""


class ListPersonalExternoDetails(viewsets.GenericViewSet):
    serializer_class = SerializerPersonalExternoDetail
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        endpoint = get_info(request)
        credentials_cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        # cuenta_eje_id = get_Persona_orList_error(persona, id=self.request.query_params["id_cuenta_eje"]).get_only_id()
        queryset = grupoPersona.objects.filter(empresa_id=credentials_cuenta_eje_id, relacion_grupo_id=6).values(
            "person_id")
        if not queryset:
            message_not_valid_cuenta_eje_id = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": credentials_cuenta_eje_id,
                        "field": "id_cuenta_eje",
                        "message": "Zero external person",
                    }
                ]
            }
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_valid_cuenta_eje_id)
            return Response(message_not_valid_cuenta_eje_id, status=status.HTTP_400_BAD_REQUEST)
        else:
            list_detalles_personalexterno = personalexterno_list(queryset)

            serializer = SerializerPersonalExternoDetail(list_detalles_personalexterno, many=True)
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Listar movimientos por cuenta (enfoque para usuario final)
"""


class ListMovementHistory(viewsets.GenericViewSet):
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request):
        endpoint = get_info(request)
        credentials_cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=log_dict)
        kward = getKward(request.GET)
        instance = get_Persona_orList_error(persona, credentials_cuenta_eje_id,
                                            endpoint,
                                            id=self.request.query_params['person_id'] )
        try:
            match = grupoPersona.objects.get(empresa_id=credentials_cuenta_eje_id,
                                             person_id=self.request.query_params['person_id'], relacion_grupo_id=6)
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": self.request.query_params['person_id'],
                        "field": "person_id",
                        "message": "No matching Persona Externa with Cuenta Eje",
                    }
                ]
            }
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_found)
            raise ValidationError(message_not_found)
        kward["tarjeta"] = request.GET.get("tarjeta")
        kward["type"] = request.GET.get("type")
        kward["cuenta_eje_id"] = credentials_cuenta_eje_id
        kward["endpoint"] = endpoint
        serializer = serializerUSertransactionesOut_TmpP1(instance, context=kward)
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


"""
    Dar de alta a Personal Externo
"""


class CreatePersonaExterna(viewsets.GenericViewSet):
    permission_classes = ()

    # permission_classes = [IsAuthenticated]
    serializer_class = SerializerPersonalExternoIn

    def create(self, request):
        endpoint = get_info(request)
        file = request.data["documento"]
        credentials_cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        if file:
            context = {
                "cuenta_eje_id": credentials_cuenta_eje_id,
                "endpoint": endpoint
            }
            serializer = self.serializer_class(data=request.data, context=context)
            if serializer.is_valid(raise_exception=True):
                num_cuenta, instance = serializer.create_personalExterno(file, credentials_cuenta_eje_id)
                pe_succesfully_created = {
                    "code": [200],
                    "status": "OK",
                    "detail": [
                        {
                            "data": "",
                            "field": "",
                            "message": "Se creo personal externo",
                            "id": instance.id,
                            "Su cuenta es": str(num_cuenta.cuenta)
                        }
                    ]
                }
                RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=pe_succesfully_created)
                return Response(pe_succesfully_created, status=status.HTTP_200_OK)
        else:
            required_document = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": file,
                        "field": "documento",
                        "message": "Document required",
                    }
                ]
            }
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=required_document)
            return Response(required_document, status=status.HTTP_400_BAD_REQUEST)


"""
    Asignar tarjetas desde una cuenta eje a un personal externo
"""


class AsignarTarjetaInntecPersonalExterno(UpdateAPIView):
    permission_classes = ()
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Asignar tarjeta a personal externo por centro de costo"]
    serializer_class = SerializerAsignarTarjetasPersonaExterna

    def create(self):
        pass

    def put(self, request):
        endpoint = get_info(request)
        credentials_cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        instance = get_Object_orList_error(cuenta,credentials_cuenta_eje_id,endpoint, cuenta=request.data["cuenta"])
        queryset = grupoPersona.objects.filter(person_id=instance.persona_cuenta_id, relacion_grupo_id=6)
        validate_cards_count(instance, request.data["tarjeta"], credentials_cuenta_eje_id, endpoint)
        if len(queryset) != 0:
            pk_empresa = credentials_cuenta_eje_id
            cuenta_eje_personal_externo = grupoPersona.objects.filter(empresa_id=pk_empresa,
                                                                      person_id=instance.persona_cuenta_id,
                                                                      relacion_grupo_id=6)
            if len(cuenta_eje_personal_externo) != 0:
                serializer = self.serializer_class(data=request.data, context={"empresa_id": pk_empresa, "endpoint": endpoint})
                if serializer.is_valid(raise_exception=True):
                    instanceP = get_Object_orList_error(persona,credentials_cuenta_eje_id, endpoint, id=instance.persona_cuenta_id)
                    tarjetas = serializer.update(instance, instanceP, credentials_cuenta_eje_id, endpoint)
                    message_card_asigned = {
                        "code": [200],
                        "status": "OK",
                        "detail": [
                            {
                                "data": request.data["tarjeta"],
                                "field": "tarjeta",
                                "message": "Se asignaron las tarjetas"
                            }
                        ]
                    }
                    RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                                      endpoint=endpoint,
                                      objJsonResponse=message_card_asigned)
                    return Response(message_card_asigned, status=status.HTTP_200_OK)
            else:
                message_pe_not_from_ce = {
                    "code": [400],
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": request.data["cuenta"],
                            "field": "cuenta",
                            "message": "External personal does not belong to cuenta eje",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_pe_not_from_ce)
                return Response(message_pe_not_from_ce, status=status.HTTP_400_BAD_REQUEST)
        else:
            message_pe_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["cuenta"],
                        "field": "cuenta",
                        "message": "External Personal not found",
                    }
                ]
            }
            RegisterSystemLog(idPersona=credentials_cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_pe_not_found)
            return Response(message_pe_not_found, status=status.HTTP_400_BAD_REQUEST)


# ---------------VISTAS AUXILIARES PARA ENDPOINT DE ASIGNAR TARJETAS A PERSONAL EXTERNO-----------------
class BuscarNumeroTarjetaInntec(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = None

    def list(self, request):
        numero_tarjeta = self.request.query_params["Tarjeta"]
        data = listCardPrueba(numero_tarjeta)  # (Prueba)
        return Response(data, status=status.HTTP_200_OK)


class AsignarTarjetaInnteCuentaEje(viewsets.GenericViewSet):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Asignar stock de tarjetas por centro de costo"]
    permission_classes = ()
    serializer_class = SerializerAsignarTarjetasCuentaEje

    def create(self, request):
        endpoint = get_info(request)
        instance = get_Object_orList_error(persona, request.query_params["id"], endpoint, id=self.request.query_params["id"])
        if grupoPersona.objects.filter(empresa_id=instance.id):
            serializer = self.serializer_class(data=request.data)
            tarjetas = request.data["tarjeta"]
            tarjetas, datos_tarjeta_inntec, token = serializer.validar_tarjetas(tarjetas)
            try:
                with transaction.atomic():
                    tarjetas = serializer.create(instance, tarjetas, datos_tarjeta_inntec, token)
                    return Response({"status": {"Se_asignaron_las_tarjetas": tarjetas}}, status=status.HTTP_200_OK)
            except Exception as e:
                message = "Ocurrio un error durante el proceso de de asignar tarjetas, Error:   " + str(e)
                error = {'field': '', "data": '', 'message': message}
                MensajeError(error)
        else:
            return Response({"status": "cuenta eje no encontrada"}, status=status.HTTP_400_BAD_REQUEST)


""" 
 Dispersiones masivas
"""


class DispersionMasiva(viewsets.GenericViewSet):
    permission_classes = ()
    permisos = ["Crear dispersión individual", "Crear dispersión masiva"]

    def create(self, request):
        endpoint = get_info(request)
        cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        validate_email_admin(cuenta_eje_id, request.data["email"], endpoint)
        cuenta_eje_instance = persona.objects.get(id=cuenta_eje_id)
        # admin_instance = request.user
        email_admin = request.data["email"]
        get_empresa: Dict = get_data_empresa(cuenta_eje_id)
        cuenta_emisor: Dict = cuenta.objects.get(persona_cuenta_id=get_empresa['id']).get_all_cuentas()
        instance_emisor = cuenta.objects.get(persona_cuenta_id=get_empresa['id'])

        # for request in request.data:
        observation: str = request.data['observations']
        person_list: List[Dict] = request.data.pop('PersonList')
        schedule_dict: Dict = request.data.pop('schedule')
        type_dispersion: str = request.data['TypeDispersion']
        monto_total: float = request.data["MontoTotal"]
        nombre_grupo: str = request.data["NombreGrupo"]
        validate_later_date(request.data["is_schedule"], schedule_dict.get("fechaProgramada"), cuenta_eje_id, endpoint)
        validate_list_persona(person_list, cuenta_eje_id, endpoint)
        validate_monto_total(person_list, monto_total, cuenta_eje_id, endpoint)
        # masivo_trans: Optional[None, int] = CreateDispersionMasiva(observation, type_dispersion).is_massive()

        context = {
            "cuenta_eje_id": cuenta_eje_id,
            "endpoint": endpoint,
            "empresa": get_empresa['name'],
            "type_dispersion": type_dispersion.upper(),
            "cuenta_emisor": cuenta_emisor,
            "instance_cuenta_emisor": instance_emisor,
            "emisor_id": instance_emisor.id,
            "observation": observation.capitalize(),
            "is_schedule": request.data['is_schedule'],
            "monto_total": monto_total,
            "nombre_emisor": cuenta_eje_instance.get_name_company(),
            "masivo_trans_id": CreateDispersionMasiva(observation, type_dispersion, cuenta_eje_id, endpoint).is_massive(),
            "logitud_lista": len(person_list),
            "email_admin": email_admin,
            "nombre_grupo": nombre_grupo.upper() if nombre_grupo else None
        }

        CreateDispersionV2(person_list, context, schedule_dict).validate_all_dispersion()

        success = MyHtppSuccess('Tu operación se realizo de manera satisfactoria.')
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonResponse=success.created())
        return Response(success.created(), status=status.HTTP_201_CREATED)


# ----------------CLASES AUXILIARES PARA DISPERSIONES MASIVAS-------------------
def create_folio():
    return random.randrange(100000, 999999, 6)


@dataclass
class CreateDispersionMasiva:
    observation: str
    type_dispersion: str
    cuenta_eje_id: int
    endpoint: str
    serializer_class = SerializerDisMassivas

    def create(self) -> int:
        data: Dict = {"observations": self.observation}
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        dispersion_id = serializer.create(serializer.data)
        return dispersion_id

    def is_massive(self):
        if self.type_dispersion.upper() == 'M':
            return self.create()
        else:
            message_must_be_massive = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": self.type_dispersion,
                        "field": "TypeDispersion",
                        "message": "Must specify a massive dispersion in order to create it",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.cuenta_eje_id, type=1,
                              endpoint=self.endpoint,
                              objJsonResponse=message_must_be_massive)
            raise ValidationError(message_must_be_massive)


@dataclass
class CreateDispersionV2:
    person_list: List[Dict]
    context: Dict[str, Any]
    schedule_dict: Dict[str, Any]
    serializer_class = SerializerDispersionTest

    def send_massive_email(self, list_beneficiario: List[Dict], list_emisor: List[Dict]) -> bool:
        return send_massive_email(list_beneficiario, list_emisor)

    def create_dispersion(self, list_validation: List, serializer: Optional, schedule_dict: Dict) -> bool:
        try:
            with atomic():
                for validated_data in list_validation:
                    monto_actual = cuenta.objects.get(cuenta=validated_data['cuenta_emisor']).get_monto_emisor()
                    serializer.create_disper(validated_data, monto_actual, schedule_dict)
        except Exception as e:
            err = MyHttpError(
                message="Ocurrio un error inesperado durante el proceso de creación de una dispersión",
                real_error=str(e))
            cuenta_eje_id = cuenta.objects.get(cuenta=list_validation[0]['cuenta_emisor']).get_person_id
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint="http://127.0.0.1:8000/api_client/v1/APIDispersionMasiva/create/",
                              objJsonResponse=err.standard_error_responses())
            raise ValidationError(err.standard_error_responses())

        return True

    def validate_all_dispersion(self):
        validation_list: List = []
        list_data_beneficiario: List[Dict] = []
        list_data_emisor: List[Dict] = []
        serializer: Optional = None

        list_data_emisor.append(self.emisor_dict_data(self.context, self.schedule_dict))
        for person in self.person_list:
            serializer = self.serializer_class(data=person, context=self.context)
            serializer.is_valid(raise_exception=True)
            validation_list.append(serializer.data)
            list_data_beneficiario.append(self.beneficiario_dict_data(person, self.context))

            if self.context['type_dispersion'] == "I":
                list_data_emisor[0]['nombre_beneficiario'] = person['nombre_beneficiario']

        self.create_dispersion(validation_list, serializer, self.schedule_dict)
        if self.context['is_schedule'] == True:
            list_data_beneficiario = []
        self.send_massive_email(list_data_beneficiario, list_data_emisor)
        return True

    def emisor_dict_data(self, context: Dict, schedule_dict: Dict) -> Dict:
        if context['is_schedule'] == True:
            return {
                "folio": create_folio(),
                "email": context['email_admin'],
                "observation": context['observation'],
                "nombre_emisor": context['nombre_emisor'],
                "fecha_operacion": schedule_dict['fechaProgramada'],
                "monto_total": context['monto_total'],
                "nombre_grupo": context['nombre_grupo']
            }
        else:
            return {
                "folio": create_folio(),
                "email": context['email_admin'],
                "observation": context['observation'],
                "nombre_emisor": context['nombre_emisor'],
                "fecha_operacion": datetime.datetime.now(),
                "monto_total": context['monto_total'],
                "nombre_grupo": context['nombre_grupo']
            }

    def beneficiario_dict_data(self, person: Dict, context: Dict) -> Dict:
        return {
            "folio": create_folio(),
            "name": person['nombre_beneficiario'],
            "email": person['email'],
            "monto": person['monto'],
            "observation": context['observation'],
            "nombre_emisor": context['nombre_emisor'],
            "fecha_operacion": datetime.datetime.now()
        }


"""
    Dispersiones individuales
"""


class DispersionIndividual(viewsets.GenericViewSet):
    serializer_class = serialzierCreateTransaction
    queryset = transferencia.objects.all()
    permission_classes = ()

    def create(self, request):
        endpoint = get_info(request)
        cuenta_eje_id = validate_credentials(request.data["username"], request.data["password"], endpoint)
        RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                          endpoint=endpoint,
                          objJsonRequest=request.data)
        cuenta_emisor_instance = get_Object_orList_error(cuenta, cuenta_eje_id, endpoint, id=request.data['cuentatransferencia'])
        client_emisor_instance = get_Object_orList_error(persona, cuenta_eje_id, endpoint, id=cuenta_emisor_instance.persona_cuenta_id)
        tarjeta_beneficiario = get_Object_orList_error(tarjeta, cuenta_eje_id, endpoint, tarjeta=request.data['cta_beneficiario'])
        validate_PE_cuenta_eje(client_emisor_instance.id, cuenta_eje_id, endpoint)
        validate_tarjeta_cuenta(request.data['cuentatransferencia'], request.data['cta_beneficiario'],
                                request.data['cuenta_emisor'], cuenta_eje_id, endpoint)
        if tarjeta_beneficiario.is_active == False:
            message_innactive_card = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["cta_beneficiario"],
                        "field": "Tarjeta",
                        "message": "Innactive Card ",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_innactive_card)
            return Response(message_innactive_card, status=status.HTTP_400_BAD_REQUEST)

        if cuenta_emisor_instance.is_active == False:
            message_innactive_account = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["cuentatransferencia"],
                        "field": "Cuenta",
                        "message": "Innactive Account ",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_innactive_account)
            return Response(message_innactive_account, status=status.HTTP_400_BAD_REQUEST)

        if cuenta_emisor_instance.monto < request.data['monto']:
            message_not_funds = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": request.data["monto"],
                        "field": "monto",
                        "message": "Not enough funds ",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_not_funds)
            return Response(message_not_funds, status=status.HTTP_400_BAD_REQUEST)
        context = {
            "endpoint": endpoint,
            "cuenta_eje_id": cuenta_eje_id
        }
        serializer = self.serializer_class(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save(tarjeta_beneficiario, cuenta_emisor_instance, client_emisor_instance, cuenta_eje_id, endpoint)
            message_success = {
                "code": [201],
                "status": "CREATED",
                "detail": [
                    {
                        "data": "",
                        "field": "",
                        "message": "Dispersion successfully created ",
                    }
                ]
            }
            RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                              endpoint=endpoint,
                              objJsonResponse=message_success)
            return Response(message_success, status=status.HTTP_201_CREATED)


"""
    Endpoint que sirve como script para ejecutar las dispersiones masivas programadas
"""


class DispersionMasivaProgramada(viewsets.GenericViewSet):
    permission_classes = ()

    # permission_classes = [IsAuthenticated]

    def list(self, request):
        programadas = transferencia.objects.filter(status_trans_id=3, programada=1)
        list_already_checked = []
        for programada in programadas:
            list_data_beneficiario: List[Dict] = []
            list_data_emisor: List[Dict] = []  # lista con los datos de los administrativos de la cuenta emisora
            monto_total = 0
            if programada.masivo_trans_id and programada.masivo_trans_id not in list_already_checked:  # si tiene un id de dispersion masiva y si ya fue verificado su turno
                instance_trans_prog = TransMasivaProg.objects.filter(
                    masivaReferida_id=programada.masivo_trans_id).first()#recupero en esta tabla la instancia con la fecha en la que debe ser ejecutada
                if instance_trans_prog:  # si existe un registro de dispersion masiva programada
                    date_programada = dateutil.parser.parse(str(instance_trans_prog.fechaProgramada)).date()
                    date_now = datetime.datetime.today().strftime('%Y-%m-%d')  # fecha de hoy

                    if str(date_programada) == str(date_now):  # la fecha programda sea hoy
                        # obtenemos las dispersiones individuales que conforman la dispersion masiva (recuperada de la tabla transferencia)
                        list_to_be_process = transferencia.objects.filter(
                            masivo_trans_id=instance_trans_prog.masivaReferida_id)
                        # por cada dispersion individual se recuperan los datos del emisor y el beneficiario, se actualizan los montos de ambos
                        # se le notifica al beneficiario via sms y se actualiza la dispersion individual a status_trans_id = 1 (liquidada)
                        for to_be_process in list_to_be_process:
                            #obtenemos la cuenta emisora
                            instance_cuenta_emisor = cuenta.objects.filter(cuenta=to_be_process.cuenta_emisor).first()
                            #obtenemos cuenta beneficiario
                            cta_beneficiario = cuenta.objects.filter(cuenta=to_be_process.cta_beneficiario).first()
                            instance_persona_beneficiaria = persona.objects.filter(
                                id=cta_beneficiario.persona_cuenta_id).first()
                            # aqui va la info del beneficiario ------------------------------------------------------------------------
                            list_data_beneficiario.append(
                                self.beneficiario_dict_data(programada, instance_persona_beneficiaria))
                            instance_cuenta_emisor.monto -= to_be_process.monto
                            instance_cuenta_emisor.save()

                            monto_total = monto_total + to_be_process.monto

                            cta_beneficiario.monto += to_be_process.monto
                            cta_beneficiario.save()
                            # se notifica al beneficiario
                            enviarSMS(to_be_process.monto, instance_persona_beneficiaria)
                            # actualizar el estado de la transferencia
                            to_be_process.status_trans_id = 1
                            to_be_process.save()
                            RegisterSystemLog(idPersona=instance_cuenta_emisor.persona_cuenta_id, type=1,
                                              endpoint="http://127.0.0.1:8000/api_client/v1/ScriptDispersionMasivaProgramada/list/",
                                              objJsonResponse={"status": "Dispersion masiva programada realizada"})
                        # aqui va el emisor su info
                        list_data_emisor = self.emisores_list_data(programada, monto_total)
                        # Se envian los correos para notificar a los beneficiario y a los emisores de la dispersion
                        send_massive_email(list_data_beneficiario, list_data_emisor)
                    # se actualiza la fecha de ejecucion de la tabla TransMasivaProg de cada una de las dispersiones que conforma a la masiva
                    list_dis_prog = TransMasivaProg.objects.filter(masivaReferida_id=programada.masivo_trans_id)
                    for dis_prog in list_dis_prog:
                        dis_prog.fechaEjecucion = datetime.datetime.today()
                        dis_prog.save()
                # lista para agrupar a todas las dispersiones masivas que o ya les toco pasar o no les toca pasar el dia de hoy
                list_already_checked.append(programada.masivo_trans_id)
        return Response({"status": "Dispersion masiva programada realizada"}, status=status.HTTP_200_OK)

    def emisores_list_data(self, instance_transferencia, monto_total) -> list:
        cuenta_emisor = cuenta.objects.filter(cuenta=instance_transferencia.cuenta_emisor).first()
        emisor = persona.objects.filter(id=cuenta_emisor.persona_cuenta_id).first()  # cuenta eje
        list_admins = get_list_admins(emisor.id)  # lista de administrativos de cuenta eje
        admins_emisores_lista = []
        for admin in list_admins:
            dict_data = {
                "folio": create_folio(),
                "email": str(admin.email),
                "observation": instance_transferencia.concepto_pago,
                "nombre_emisor": instance_transferencia.nombre_emisor,
                "fecha_operacion": datetime.datetime.now(),
                "monto_total": monto_total,
                "nombre_grupo": ""
            }
            admins_emisores_lista.append(dict_data)
        return admins_emisores_lista

    def beneficiario_dict_data(self, instance_transferencia, instance_persona) -> Dict:
        return {
            "folio": create_folio(),
            "name": instance_persona.name,
            "email": instance_persona.email,
            "monto": instance_transferencia.monto,
            "observation": instance_transferencia.concepto_pago,
            "nombre_emisor": instance_transferencia.nombre_emisor,
            "fecha_operacion": datetime.datetime.now()
        }
