from typing import ClassVar

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.transaction import atomic
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status, serializers

from apps.api_stp.exc import StpmexException
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from apps.logspolipay.manager import RegisterLog
from apps.services_pay.api.mobile.serializers.transmitter_serializer import SerializerTransmitter, \
    SerializerTransmitterOut, SerializerRefrence, SerializerTransmitterHaveReference, SerializerPayTransmitter, \
    SerializerFrequentTransmitterOut, SerializerCheckBalanceRedEfectiva, SerializerCheckCommissionRedEfectiva
from apps.services_pay.management import existing_account, generate_list_frequents, get_info_account_from_person, \
    create_response_trantype30, \
    create_response_trantype32
from apps.services_pay.models import Transmitter, Fee, TransmitterHaveReference, Reference, Frequents
from apps.users.models import persona


class TransmitterCrud(GenericViewSet):
    serializer_class = SerializerTransmitter

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"status": [
                {
                    "code": 201,
                    "status": "SUCCESS",
                    "field": "",
                    "data": "",
                    "message": "Emisor creado correctamente"
                }]}, status=status.HTTP_200_OK)

    def list(self, request):
        keywords = {}
        try:
            id = self.request.query_params['id']
            keywords['catRel_id'] = id
        except:
            keywords = {}
        query = Transmitter.objects.filter(**keywords)
        serializer = SerializerTransmitterOut(query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        instance = Transmitter.objects.get(id=pk)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, serializer.validated_data)
            return Response(status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        instance = Transmitter.objects.get(id=pk)
        Fee.objects.filter(transmitter_id=pk).delete()
        TransmitterHaveReference.objects.filter(transmitter_id=pk).delete()
        if instance.image != None:
            instance.image.delete()
        instance.delete()
        return Response(status=status.HTTP_200_OK)


class ReferenceCrud(GenericViewSet):
    serializer_class = SerializerRefrence

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"status": [
                {
                    "code": 201,
                    "status": "SUCCESS",
                    "field": "",
                    "data": "",
                    "message": "Referencia creada correctamente"
                }]}, status=status.HTTP_200_OK)

    def list(self, request):
        query = Reference.objects.all()
        serializer = self.serializer_class(query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        Reference.objects.get(id=pk).delete()
        return Response(status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        instance = Reference.objects.get(id=pk)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, serializer.validated_data)
            return Response(status=status.HTTP_200_OK)


class TransmitterHaveReferenceCrud(GenericViewSet):
    serializer_class = SerializerTransmitterHaveReference

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(status=status.HTTP_200_OK)

    def list(self, request):
        query = TransmitterHaveReference.objects.all()
        serializer = self.serializer_class(query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        TransmitterHaveReference.objects.get(id=pk).delete()
        return Response(status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        instance = TransmitterHaveReference.objects.get(id=pk)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance, serializer.validated_data)
            return Response(status=status.HTTP_200_OK)


class PayTransmitterCreate(GenericViewSet):
    serializer_class = SerializerPayTransmitter
    _log: ClassVar[RegisterLog] = RegisterLog

    def create(self, request):
        log = self._log(request.user, request)
        log_efectiva_obj = None

        try:
            with atomic():
                # guardar la peticion en el log de polipay
                endpoint = get_info(request)
                persona = existing_account(request.data['cuenta'], endpoint)
                log.json_request(request.data)
                context = {"person_id": persona, "endpoint": endpoint, "log": log}
                serializer = self.serializer_class(data=request.data, context=context)
                if serializer.is_valid(raise_exception=True):
                    response, log_efectiva_obj = serializer.create(serializer.validated_data)
                    if response.solicitaResult != 0:
                        raise ValueError("Error al realizar el pago")

                    if response.solicitaResult == 0:
                        log_efectiva_obj.save()

        except (TypeError, IndexError) as e:
            RegisterSystemLog(idPersona=persona, type=1, endpoint=endpoint, objJsonResponse=str(e))
            return Response({"status": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except (ValueError, ObjectDoesNotExist, IntegrityError) as e:
            RegisterSystemLog(idPersona=persona, type=1, endpoint=endpoint, objJsonResponse=str(e))
            log_efectiva_obj.save()
            return Response({"status": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        else:
            dict_person = get_info_account_from_person(persona)
            message_request_succesfull = {"status": [response['MsgTicket']['MsgTicket']['Msg']], "data": dict_person}
            RegisterSystemLog(idPersona=persona, type=1, endpoint=endpoint, objJsonResponse=message_request_succesfull)
            return Response(message_request_succesfull, status=status.HTTP_200_OK)


class FrequentTransmitterRD(GenericViewSet):
    serializer_class = SerializerFrequentTransmitterOut

    def list(self, request):
        RegisterSystemLog(idPersona=request.user.id, type=1, endpoint=get_info(request), objJsonRequest=request.data)
        query = Frequents.objects.select_related('transmmiter_Rel').filter(user_rel=request.user.id)
        list_frequents = generate_list_frequents(query)
        serializer = self.serializer_class(list_frequents, many=True)

        RegisterSystemLog(idPersona=request.user.id, type=1, endpoint=get_info(request),
                          objJsonResponse=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        url: str = get_info(request)
        user: persona = request.user

        try:
            with atomic():
                RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=url, objJsonRequest=request.data)
                instance_frequent = Frequents.objects.filter(user_rel=user, transmmiter_Rel=pk)

                # Verifica que exista el servicio como frecuente
                if not instance_frequent:
                    err = {"status": "Id emisor no encontrado"}
                    RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=url, objJsonResponse=err)
                    raise serializers.ValidationError(err)

                instance_frequent2 = Frequents.objects.get(user_rel=user, transmmiter_Rel=pk)
                instance_transmmitter = Transmitter.objects.get(id=instance_frequent2.transmmiter_Rel.id)

                instance_frequent.delete()

        except (ObjectDoesNotExist, ValueError, TypeError, IntegrityError) as e:
            err = {"status": "Ocurrio un error al eliminar la cuenta frecuente"}
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=url, objJsonResponse=str(e))
            return Response(err)
        else:
            succ = {"status": f"El Servicio {instance_transmmitter.name_transmitter} \n ha sido borrado de frecuentes"}
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=url, objJsonResponse=succ)
            return Response(succ, status=status.HTTP_200_OK)


# (EduCed) Clase para consultar el saldo a pagar por medio de la referencia (red efectiva)
class CheckBalanceRedEfectiva(GenericViewSet):
    serializer_class = SerializerCheckBalanceRedEfectiva

    def create(self, request):
        endpoint: str = get_info(request)
        user: persona = request.user

        try:
            with atomic():
                RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonRequest=request.data)

                context = {
                    "person_id": persona,
                    "endpoint": endpoint
                }

                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                response, ticket = serializer.create()
                movil_response = create_response_trantype30(response, context)

        except (ObjectDoesNotExist, ValueError, TypeError, IntegrityError) as e:
            err = {"status": "Ocurrio un error al consultar el saldo a pagar"}
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonResponse=err)
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        else:
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonResponse=movil_response)
            return Response(movil_response, status=status.HTTP_200_OK)


# (EduCed) Clase para consultar el saldo a pagar por medio de la referencia (red efectiva)
class CheckCommissionRedEfectiva(GenericViewSet):
    serializer_class = SerializerCheckCommissionRedEfectiva

    def create(self, request):
        endpoint = get_info(request)
        user: persona = request.user
        try:
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonRequest=request.data)

            with atomic():
                context = {
                    "person_id": persona,
                    "endpoint": endpoint
                }

                serializer = self.serializer_class(data=request.data, context=context)
                serializer.is_valid(raise_exception=True)
                response, ticket = serializer.create()
                movil_response = create_response_trantype32(response, context)

        except (ObjectDoesNotExist, ValueError, TypeError, IntegrityError) as e:
            err = {"status": "Ocurrio un error al consultar la comisión"}
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonResponse=err)
            return Response(err, status=status.HTTP_400_BAD_REQUEST)
        else:
            RegisterSystemLog(idPersona=user.get_only_id(), type=1, endpoint=endpoint, objJsonResponse=movil_response)
            return Response(movil_response, status=status.HTTP_200_OK)
