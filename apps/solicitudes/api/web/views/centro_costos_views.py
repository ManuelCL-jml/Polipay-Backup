from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from django.db import IntegrityError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet
from rest_framework import pagination, status
from rest_framework.response import Response

from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.logspolipay.manager import RegisterLog
from apps.permision.permisions import BlocklistPermissionV2
from apps.solicitudes.api.web.serializers.centro_costos_serializers import *
from apps.solicitudes.management import GenerarPDFSaldos
from apps.transaction.models import transferencia
from apps.users.management import *
from apps.users.models import *
from apps.solicitudes.models import *

""" - - - - - - V i s t a s   P r i n c i p a l e s - - - - - - """


class Solicitud(GenericViewSet):
    serializer_class_get = SerializerSolicitudOut

    def list(self, request):
        queryset = Solicitudes.objects.all()
        serializer = self.serializer_class_get(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerificacionDocumentos(GenericViewSet):
    serializer_class_get = SerializerVerificarDocumentoOut
    serializer_class_put = SerializerDocumentsIn

    def list(self, request):
        pk_Centro_Costos = self.request.query_params["id"]
        instanceGP = get_Object_orList_error(grupoPersona, empresa_id=pk_Centro_Costos, relacion_grupo_id=4)

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        queryset = persona.objects.filter(id=instanceGP.empresa_id)
        serializer = self.serializer_class_get(queryset, many=True)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        context = {'request_user_authorization': request.user}
        document_id = self.request.query_params["documento_id"]

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        instance = get_Object_orList_error(documentos, pk=document_id)
        serializer = self.serializer_class_put(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.update_Document(instance)
        R = {"status": "Documentos actualizados"}
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=R)
        return Response(R, status=status.HTTP_200_OK)


""" D e t a l l a r   S o l i c i t u d e s """


class RetrieveCentroCostos(GenericViewSet):
    serializer_class = SerializerRetrieveCentroCostos

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        gp = self.get_queryset(grupoPersona, empresa_id=self.request.query_params['id'])
        serializer_gp = self.serializer_class(instance=gp)

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        documents = filter_all_data_or_return_none(documentos, person_id=gp.empresa_id)
        serializer_doc_cc = SerializerDocumentsOut(instance=documents, many=True)

        documents_rl = filter_all_data_or_return_none(documentos, person_id=gp.person_id)
        serializer_doc_rl = SerializerDocumentsOut(instance=documents_rl, many=True)
        R = {
            "Centro_Costos": serializer_gp.data,
            "Documento_CC": serializer_doc_cc.data,
            "Documentos_RL": serializer_doc_rl.data
            }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=R)
        return Response(R, status=status.HTTP_200_OK)


class DetailSolicitudBajaCentroCostos(RetrieveAPIView):
    serializer_class = SerializerDetallarBajaCentroCostosOut

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        id = request.query_params['id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        queryset = select_related("domicilioPersona", domicilio, domicilioPersona_id=id, historial=False)
        serializer = self.serializer_class(instance=queryset)

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class SolicitudAperturaCentroCostos(GenericViewSet):
#     serializer_class_get = SerializerSolicitudAperturaCentroCostosOut
#     serializer_class_update = SerializerAuthorizeIn
#     permission_classes = ()
#
#     def list(self,request):
#         pk_Centro_Costos = self.request.query_params["id"]
#         instanceGP = filter_Object_Or_Error(grupoPersona, empresa_id=pk_Centro_Costos, relacion_grupo_id=4)
#         instanceOneValue = instanceGP.last()
#         instance = persona.objects.filter(id=instanceOneValue.empresa_id)
#         serializer = self.serializer_class_get(instance, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
#
#     def put(self,request):
#         pk_document = self.request.query_params["DocumenId"]
#         instance = get_Object_orList_error(documentos,id=pk_document)
#         serializer = self.serializer_class_update(data=request.data)
#         if serializer.is_valid(raise_exception=True):
#             pk_user = request.user
#             serializer.authorization(instance,pk_user)
#             return Response({"status":"listo"},status=status.HTTP_200_OK)


class SolicitarSaldos(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Solicitar saldo para la cuenta"]
    serializer_class = SerializerSolicitarSaldosIn

    def create(self, request):
        person_instance = persona.objects.get(id=self.request.query_params['id'])

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        cuenta_instance = cuenta.objects.filter(persona_cuenta__id=person_instance.id).values('cuentaclave').first()

        context = {
            'persona_saldo': person_instance.id,
            'persona_saldo_name': person_instance.name,
            'tipo_solicitud': 6,
            'nombre': 'Solicitud de saldos',
            'monto_req_min': request.data['monto_req_min'],
            'monto_total': request.data['monto_total'],
            'referencia': 'REFSSOL' + str(Code_card(10)),
            'clave': cuenta_instance
        }
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        document_id = serializer.create()

        R = {"status": f'Tu solicitud ha sido enviada satisfactoriamente y ha quedado en proceso de verificación',
             "referencia": context['referencia'],
             "document_id": document_id}

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)
        return Response(R, status=status.HTTP_201_CREATED)


class ListSolicitudesCuentaEje(ListAPIView):
    serializer_class = SerializerListSolicitudesCuentaEje

    def get_queryset(self, *args, **kwargs):
        return filter_data_or_return_none(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        id = request.query_params['id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        gp = grupoPersona.objects.filter(empresa_id=id, relacion_grupo_id=1)
        serializer = self.serializer_class(instance=gp, many=True)

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class AutorizarSolicitudSaldos(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Autorizar solicitud de saldo por grupo"]
    serializer_class = SerializerAutorizarSolicitudSaldos

    def get_queryset(self, *args, **kwargs):
        return get_Object_orList_error(*args, **kwargs)

    def create(self, request):
        pass

    def put(self, request):
        try:
            with atomic():
                log = RegisterLog(request.user, request)
                id = request.query_params['cuenta_eje']
                log.json_request(request.data)

                instance_solicitud = Solicitudes.objects.get(id=request.data['solicitud'], personaSolicitud_id=id)

                data_solicitud = instance_solicitud.get_solicitud_transfer()
                instance_cuenta = cuenta.objects.get(persona_cuenta_id=id)

                context = {
                    "empresa_id": id,
                    "referencia": data_solicitud['referencia'],
                    "monto_req_min": data_solicitud['monto_req_min'],
                    "log": log
                }

                serializer = self.serializer_class(data=request.data, context=context)

                if serializer.is_valid(raise_exception=True):
                    instance_cuenta.monto += instance_solicitud.monto_total
                    comision = instance_solicitud.monto_total - instance_solicitud.monto_req_min
                    instance_cuenta.monto -= round(comision, 2)
                    instance_cuenta.save()

                    transferencia.objects.trans_rec_saldos(
                        nombre_beneficiario=data_solicitud['nombre'],
                        fecha_creacion=data_solicitud['fecha_solicitud'],
                        cta_beneficiario=instance_cuenta.cuenta,
                        referencia=data_solicitud['referencia'],
                        monto=data_solicitud['monto_total'],
                        saldo_remanente=instance_cuenta.monto + round(comision, 2)
                    )
                    transferencia.objects.transferencia_terceros_saldos(
                        nombre_emisor=data_solicitud['nombre'],
                        cuenta_emisor=instance_cuenta.cuenta,
                        monto=round(comision, 2),
                        referencia=data_solicitud['referencia'],
                        saldo_remanente=instance_cuenta.monto
                    )
                    serializer.update(instance_solicitud, serializer.validated_data)
                    R = {"status": "La operacion se realizo con exito"}
                    RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                                      objJsonRequest=R)
                return Response(R, status=status.HTTP_200_OK)
        except IntegrityError as e:
            RE = {'code': 400,
                  'status': 'error',
                  'message': 'Ocurrio un error inesperado al momento de crear la transaccion',
                  'detail': str(e)}
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=RE)
            raise ValidationError(RE)


class SolicitarTarjetasCuentaEje(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Solicitar stock de tarjetas por grupo"]
    serializer_class = SerializerSolicitarTarjetasCuentaEjeIn

    def create(self, request):
        cuenta_eje = self.request.query_params['cuenta_eje']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        gpersona_instance = grupoPersona.objects.get(empresa_id=cuenta_eje, relacion_grupo_id=1).get_only_id_empresa()
        instance_cuenta_CE = get_Object_orList_error(cuenta, persona_cuenta_id=gpersona_instance)

        context = {
            'instance_cuenta_CE': instance_cuenta_CE,
            'CE_solicitud': gpersona_instance,
            'tipo_solicitud': 7,
            'nombre_solicitud': 'Solicitud Tarjetas CE',
            'cant_clasica': request.data['Clasica'],
            'cant_platino': request.data['Platino'],
            'cant_dorada': request.data['Dorada'],
            'monto_req_min': request.data['Subtotal'],
            'monto_total': request.data['monto_total_iva']
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()
        solicitud_instance = Solicitudes.objects.last()

        R = {'code': 200,
             'status': 'OK',
             'message': f'Se ha realizado un cargo por {solicitud_instance.monto_total} a su cuenta',
             'detail': f'{solicitud_instance.monto_total}'}

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=serializer.data)

        return Response(R)


class GetCostoUnitariosTarjetas(ListAPIView):
    def list(self, request, *args, **kwargs):
        costo_tarjeta = cat_tarjeta.objects.all().values('id', 'nombreCom', 'costoUnit')
        return Response(costo_tarjeta)


class RequestsCardDetail(ListAPIView):
    def list(self, request, *args, **kwargs):
        id = request.query_params['solicitud_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        solicitud = Solicitudes.objects.values('dato_json', 'monto_req_min', 'monto_total').filter(id=id,
                                                                                                   tipoSolicitud_id=7)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=solicitud)
        return Response(solicitud)


class ChangeStatusToCardRequests(GenericViewSet):
    serializer_class = SerializerChangeStatusToCardRequest

    def create(self, request):
        log = RegisterLog(request.user, request)
        solicitud_id = self.request.query_params['solicitud_id']
        log.json_request(request.query_params)

        instance_solicitud = get_Object_orList_error(Detalle_solicitud, sol_rel=solicitud_id)

        context = {
            'Solicitud': solicitud_id,
            'edo_solicitud': instance_solicitud.edodetail_id,
            'log': log
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.create()
        R = {"code": 200, "status": "OK", "message": "La operacion se realizo con exito"}
        log.json_response(R)
        return Response(R)

    def put(self, request):
        log = RegisterLog(request.user, request)
        solicitud_id = self.request.query_params['solicitud_id']
        log.json_request(request.query_params)

        instance_solicitud = get_Object_orList_error(Detalle_solicitud, sol_rel=solicitud_id)

        context = {
            'edo_solicitud': instance_solicitud.edodetail_id,
            'log': log
        }

        serializer = SerializerChangeStatusToCardRequestUpdate(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.update(instance_solicitud, serializer.validated_data)

            R = {"Code": 200, "status": "UPDATE", "message": "La operacion se realizo con exito"}
            log.json_response(R)
            return Response(R, status=status.HTTP_200_OK)


class ListStatusToChangeCardRequest(ListAPIView):

    def list(self, request, *args, **kwargs):
        status = EdoSolicitud.objects.values('id', 'nombreEdo').filter(Q(id=1) | Q(id=5) | Q(id=6) | Q(id=7))
        return Response(status)


# (ManuelCalixtro 18/01/2022) Endpoint para solicitar tarjetas desde un centro de costos
class RequestCardsCostCenters(GenericViewSet):
    serializer_class = SerializerRequestCardsCostCenter

    def create(self, request):
        try:
            company_id = self.request.query_params['company_id']
            cost_center_id = self.request.query_params['cost_center_id']
            colaborador: persona = self.request.user

            log_dict = {
                "params": request.query_params,
                "body": request.data
            }
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=log_dict)

            instance_cost_center = grupoPersona.objects.get(empresa_id=company_id, person_id=cost_center_id, relacion_grupo_id=5)

            context = {
                'personaSolicitud_id': instance_cost_center.person_id,
                'colaborador': colaborador.get_full_name()
            }

            serializer = self.serializer_class(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.create(serializer.validated_data)
            success = MyHtppSuccess('Tu solicitud de tarjetas esta en proceso')

            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=success)

            return Response(success.standard_success_responses(), status=status.HTTP_200_OK)
        except (ObjectDoesNotExist, IntegrityError, ValueError, KeyError) as e:
            err = MyHttpError(message='Verifique que los parametros ingresados sean correctos', real_error=str(e))
            RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                              objJsonRequest=err)
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


# (ManuelCalixtro 18/01/2022) Endpoint para cancelar una solicitud de tarjetas
class CancelRequestCards(GenericViewSet):
    serializer_class = SerializerCancelCardsRequest

    def create(self):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        solicitud_id = self.request.query_params['request_id']
        log.json_request(request.query_params)

        get_card_request = get_Object_orList_error(Solicitudes, id=solicitud_id, tipoSolicitud_id=9)

        context = {
            'status_request': get_card_request.estado_id,
            'log': log
        }

        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.update(get_card_request, serializer.validated_data)
        success = MyHtppSuccess('La solicitud de tarjetas ha sido cancelada exitosamente', extra_data=f'fecha_solicitud:{get_card_request.fechaSolicitud}, {get_card_request.get_name_persona_solicitud()}')
        log.json_response(success.standard_success_responses())
        return Response(success.standard_success_responses(), status=status.HTTP_200_OK)


# (ManuelCalixtro 19/01/2022) listar las tarjetas que tiene disponibles una cuenta eje y/o centro de costos
class StockCardsInCompany(RetrieveAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver stock de tarjetas por grupo"]

    def get(self, request, *args, **kwargs):
        company_id = self.request.query_params['company_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        get_classics_available_cards = tarjeta.objects.filter(clientePrincipal_id=company_id, status="04", tipo_tarjeta_id=1)
        get_platino_available_cards = tarjeta.objects.filter(clientePrincipal_id=company_id, status="04", tipo_tarjeta_id=2)
        get_dorada_available_cards = tarjeta.objects.filter(clientePrincipal_id=company_id, status="04", tipo_tarjeta_id=3)

        R = {'Clasicas':len(get_classics_available_cards), 'Platino': len(get_platino_available_cards), 'Doradas': len(get_dorada_available_cards)}
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=R)
        return Response(R)


# (ManuelCalixtro 20/01/2022) Endpoint para listar las solicitudes de tarjetas de todos los centros de costos con filtro
class ListRequestAllCostCenter(ListAPIView):

    def list(self, request, *args, **kwargs):
        company_id = self.request.query_params['company_id']
        centro_costos = self.request.query_params['centro_costos']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        get_cost_centers = grupoPersona.objects.get_list_actives_cost_centers_id(company_id)
        get_request_all_cost_centers = Solicitudes.objects.filter_request_cards_all_cost_center(centro_costos, get_cost_centers, date1, date2)

        for i in get_request_all_cost_centers:
            i['dato_json'] = json.loads(i.get('dato_json'))

        page = self.paginate_queryset(get_request_all_cost_centers)
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=page)
        return self.get_paginated_response(page)


# (ManuelCalixtro 21/01/2022) Endpoint para listar las solicitudes de tarjetas de un centro de costos con filtro
class ListRequestCostCenter(ListAPIView):

    def list(self, request, *args, **kwargs):
        cost_center_id = self.request.query_params['cost_center_id']
        estado = self.request.query_params['status']
        date1 = self.request.query_params['start_date']
        date2 = self.request.query_params['end_date']

        size = self.request.query_params['size']
        pagination.PageNumberPagination.page_size = size

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        get_request_cost_center = Solicitudes.objects.filter_request_cards_cost_center(cost_center_id, estado, date1, date2)

        for i in get_request_cost_center:
            i['dato_json'] = json.loads(i.get('dato_json'))

        page = self.paginate_queryset(get_request_cost_center)

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=page)
        return self.get_paginated_response(page)


# (ManuelCalixtro 21/01/2022) Endpoint para asignar las tarjetas solcitadas a un centro de costos
class AssignCardsCostCenter(GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Asignar stock de tarjetas por centro de costo"]
    serializer_class = SerializerAssingCardsCostCenter

    def create(self):
        pass

    def put(self, request):
        log = RegisterLog(request.user, request)
        cost_center_id = self.request.query_params['cost_center_id']
        company_id = self.request.query_params['company_id']
        request_id = self.request.query_params['request_id']
        log.json_request(request.query_params)

        get_account = cuenta.objects.get(persona_cuenta_id=cost_center_id).get_only_id()

        context = {
            "company_id": company_id,
            'cost_center_id': cost_center_id,
            'request_id': request_id,
            'get_account': get_account,
            'log': log
        }

        cost_center = grupoPersona.objects.get(person_id = cost_center_id, relacion_grupo_id=5)
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.update(cost_center, serializer.validated_data)
        success = MyHtppSuccess('Se han asignado las tarjetas al Centro de Costos')
        log.json_response(success.standard_success_responses())
        return Response(success.standard_success_responses(), status=status.HTTP_200_OK)


# (ManuelCalixtro 31/01/2022) Endpoint que lista el id y el numero de tarjeta para poder asignarlas
class ListAvaliableCards(ListAPIView):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver stock de tarjetas por centro de costo"]

    def list(self, request, *args, **kwargs):
        cuenta_eje = self.request.query_params['company_id']

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        get_classics_cards = tarjeta.objects.filter(clientePrincipal_id=cuenta_eje, status="04", tipo_tarjeta_id=1).values('id', 'tarjeta')
        get_platinum_cards = tarjeta.objects.filter(clientePrincipal_id=cuenta_eje, status="04", tipo_tarjeta_id=2).values('id', 'tarjeta')
        get_golden_cards = tarjeta.objects.filter(clientePrincipal_id=cuenta_eje, status="04", tipo_tarjeta_id=3).values('id', 'tarjeta')

        R = {'Clasicas': get_classics_cards, 'Platino': get_platinum_cards, 'Doradas': get_golden_cards}

        return Response(R)


# (ManuelCalixtro 31/01/2022) Endpoint para ver los detalles de una solicitud de tarjetas desde un centro de costos
class CardsRequestDetails(RetrieveAPIView):

    def get(self, request, *args, **kwargs):
        log = RegisterLog(request.user, request)
        request_id = self.request.query_params['request_id']
        log.json_request(request.query_params)

        get_request = Solicitudes.objects.filter(id=request_id, tipoSolicitud_id=9).values(
            'fechaSolicitud',
            'dato_json',
            'estado__nombreEdo'
        )
        for i in get_request:
            i['dato_json'] = json.loads(i.get('dato_json'))

        log.json_response({get_request})
        return Response(get_request)







