import datetime
import json

from django.db.models import Q
from django.db.transaction import atomic
from django.db import IntegrityError

from rest_framework.serializers import *

from MANAGEMENT.Utils.utils import PDFBase64File
from apps.commissions.models import Commission
from apps.solicitudes.models import *
from apps.solicitudes.management import get_number_attempts, GenerarPDFSaldos, changueStatusRequest
from apps.solicitudes.message import send_massive_email, send_email_authorization

from apps.transaction.models import bancos

from apps.users.management import get_Object_orList_error, filter_data_or_return_none, Code_card
from apps.users.models import *
from polipaynewConfig.exceptions import get_Object_Or_Error, ErrorsList

""" - - - - - - S e r i a l i z a d o r e s   D e   E n t r a d a - - - - - - """


class SerializerDocumentsIn(Serializer):
    status = CharField()
    comentario = CharField(allow_blank=True, allow_null=True)

    def validate(self, attrs):
        admin_instance = self.context['request_user_authorization'].get_staff_or_superusers()

        if admin_instance['is_staff']:
            return attrs

        if admin_instance['is_superuser']:
            return attrs

        raise ValidationError({'status': ['No tienes permiso de realiza esta acción']})

    def update_Document(self, instance):
        admin_instance = self.context['request_user_authorization'].get_staff_or_superusers()
        instance.status = self.validated_data.get("status", instance.status)
        instance.comentario = self.validated_data.get("comentario", instance.comentario)
        if instance.status == "C":
            instance.authorization = True
            instance.dateauth = datetime.datetime.now()
            instance.userauth_id = admin_instance['id']
        instance.save()
        return True


# class DocumentIn(Serializer):
#     comentario = CharField()
#     person_id = IntegerField()
#     status = CharField(default='P')
#     authorization = BooleanField(default=False)
#     documento = PDFBase64File(required=True)
#     load = DateTimeField(default=datetime.datetime.now())
#     historial = BooleanField(default=0)
#     tdocumento_id = IntegerField(default=19)
#
#     def create(self, validated_data):
#         instance = documentos.objects.create()
#         return instance

""" - - - - - - S e r i a l i z a d o r e s   D e   S a l i d a - - - - - - """


class SerializerSolicitudOut(Serializer):
    id = ReadOnlyField()
    fechaSolicitud = DateTimeField()
    intentos = IntegerField()
    CentoCostos = SerializerMethodField()
    Estado = SerializerMethodField()
    TipoSolicitud = SerializerMethodField()

    def get_Estado(self, obj: Estado):
        estados = EdoSolicitud.objects.filter(id=obj.estado_id)
        return SerializerEdoSolicitudOut(estados, many=True).data

    def get_TipoSolicitud(self, obj: TipoSolicitud):
        Tsolicitud = TipoSolicitud.objects.filter(id=obj.tipoSolicitud_id)
        return SerializerTipoSolicitudOut(Tsolicitud, many=True).data

    def get_CentoCostos(self, obj: CentoCostos):
        queryset = persona.objects.filter(id=obj.personaSolicitud_id)
        return SerialicerCentoCostosOut(queryset, many=True).data


class SerializerTipoSolicitudOut(Serializer):
    id = ReadOnlyField()
    nombreSol = CharField()


class SerializerEdoSolicitudOut(Serializer):
    id = ReadOnlyField()
    nombreEdo = CharField()


class SerialicerCentoCostosOut(Serializer):
    id = ReadOnlyField()
    name = CharField()


class SerializerDocumentsOut(Serializer):
    id = CharField()
    documento = FileField()


class SerializerDocumentOut(Serializer):
    id = ReadOnlyField()
    documento = FileField()
    Tipodocumento = SerializerMethodField()
    authorization = BooleanField()
    status = CharField()

    def get_Tipodocumento(self, obj: Tipodocumento):
        # queryset = TDocumento.objects.get(nombreTipo=obj.id)
        queryset = TDocumento.objects.filter(id=obj.tdocumento_id)
        return SerializerTipoDocumentoOut(queryset, many=True).data


class SerializerTipoDocumentoOut(Serializer):
    id = ReadOnlyField()
    nombreTipo = CharField()


class SerializerVerificarDocumentoOut(Serializer):
    id = ReadOnlyField()
    name = CharField()
    last_name = CharField()
    rfc = CharField()
    DatosTransferenciaFinal = SerializerMethodField()
    Documents = SerializerMethodField()
    domicilioFiscal = SerializerMethodField()

    def get_DatosTransferenciaFinal(self, obj: DatosTransferenciaFinal):
        queryset = persona.objects.get(id=obj.id)
        instance = bancos.objects.get(clabe=obj.banco_clabe)
        return {
            'institucion': instance.institucion,
            'clave_traspaso': queryset.clave_traspaso
        }

    def get_Documents(self, obj: Documents):
        instance = documentos.objects.filter(person_id=obj.id)
        return SerializerDocumentOut(instance, many=True).data

    def get_domicilioFiscal(self, obj: domicilioFiscal):
        queryGP = grupoPersona.objects.get(empresa_id=obj.id)
        queryPL = persona.objects.get(id=queryGP.person_id)
        instance = domicilio.objects.filter(domicilioPersona_id=queryPL.id)
        return SerializerAddressOut(instance, many=True).data


class SerializerAddressOut(Serializer):
    id = ReadOnlyField()
    codigopostal = CharField()
    colonia = CharField()
    alcaldia_mpio = CharField()
    estado = CharField()
    calle = CharField()
    no_exterior = CharField()
    no_interior = CharField()
    pais = CharField()


""" - - - - - - S e r i a l i z a d o r e s   d e   D e t a l l a d o - - - - - - """


class SerializerRetrieveCentroCostos(Serializer):
    solicitudes = SerializerMethodField()
    empresa_id = SerializerMethodField()
    domicilio_fiscal = SerializerMethodField()
    person_id = SerializerMethodField()

    def get_empresa_id(self, obj: empresa_id):
        person_instance = get_Object_orList_error(persona, id=obj.empresa_id)
        bank_instance = get_Object_orList_error(bancos, clabe=person_instance.banco_clabe)

        return {
            'Centro_costo': person_instance.name,
            'rfc': person_instance.rfc,
            'clabe_traspaso': person_instance.clave_traspaso,
            'banco_clabe': bank_instance.institucion,
        }

    def get_solicitudes(self, obj: solicitudes):
        person_instance = get_Object_orList_error(persona, id=obj.empresa_id)
        solicitud_instance = Solicitudes.objects.filter(personaSolicitud_id=person_instance.id)

        lista = []

        for s in solicitud_instance:
            tipo_solcitud_instance = get_Object_orList_error(TipoSolicitud, id=s.tipoSolicitud_id)

            data = {
                'id': person_instance.id,
                'Tipo_solicitud': tipo_solcitud_instance.nombreSol,
            }

            lista.append(data)

        return lista

    def get_person_id(self, obj: person_id):
        person_instance = get_Object_Or_Error(persona, id=obj.person_id)
        return {
            'id': person_instance.id,
            'name': person_instance.get_full_name(),
            'email': person_instance.email,
            'RFC': person_instance.rfc
        }

    def get_domicilio_fiscal(self, obj: domicilio_fiscal):
        queryset = domicilio.objects.filter(domicilioPersona_id=obj.empresa_id, historial=False)
        datos = []

        for d in queryset:
            instance = domicilio.objects.get(domicilioPersona=d.domicilioPersona_id, historial=d.historial)
            datos.append(instance)

        return SerializerAddressOut(datos, many=True).data


class SerializerDetallarBajaCentroCostosOut(Serializer):
    empresa_id = SerializerMethodField()

    def get_empresa_id(self, obj: empresa_id):
        data = {}
        for i in obj:
            data_centro_costos = i.domicilioPersona.get_centro_costo_all_data()
            doc = filter_data_or_return_none(documentos, person_id=data_centro_costos['id'], tdocumento=15,
                                             historial=False)

            data = {
                "empresa": data_centro_costos,
                "domicilio": i.get_domicilio(),
                "banco": get_Object_orList_error(bancos, clabe=data_centro_costos['banco_clabe']).get_institucion(),
                "documento": SerializerDocumentsOut(doc).data
            }

        return data


# class SerializerSolicitudAperturaCentroCostosOut(Serializer):
#     id = ReadOnlyField()
#     last_name = CharField()
#     rfc = CharField()
#     RepresentanteLegal = SerializerMethodField()
#     DomicilioFiscal = SerializerMethodField()
#     DatosTransferenciaFinal = SerializerMethodField()
#     banco_clabe = SerializerMethodField()
#     documents = SerializerMethodField()
#
#     def get_DomicilioFiscal(self, obj: DomicilioFiscal):
#         queryGP = grupoPersona.objects.get(empresa_id=obj.id)
#         queryPL = persona.objects.get(id=queryGP.person_id)
#         instance = domicilio.objects.filter(domicilioPersona_id=queryPL.id)
#         return SerializerAddressOut(instance, many=True).data
#
#     def get_banco_clabe(self, obj: banco_clabe):
#         instance_banco = get_Object_orList_error(bancos, clabe=obj.banco_clabe)
#         return {
#             'banco': instance_banco.institucion
#         }
#
#     def get_DatosTransferenciaFinal(self, obj: DatosTransferenciaFinal):
#         queryset = persona.objects.get(id=obj.id)
#         return {
#             'clave_traspaso': queryset.clave_traspaso
#         }
#
#     def get_RepresentanteLegal(self, obj: RepresentanteLegal):
#         queryset = filter_Object_Or_Error(grupoPersona, relacion_grupo=4, empresa_id=obj.id)
#         datos = []
#         for data in queryset:
#             instance = persona.objects.get(id=data.person_id)
#             datos.append(instance)
#         return SerializerRepresentanteLegal(datos, many=True).data
#
#     def get_documents(self, obj: documents):
#         queryset = documentos.objects.filter(person_id=obj.id)
#         return SerializerDocumentsOut(queryset, many=True).data

class SerializerSolicitarSaldosIn(Serializer):
    def create(self, **kwargs):
        persona_saldo = self.context['persona_saldo']
        persona_saldo_name = self.context['persona_saldo_name']
        tipo_solicitud_id = self.context['tipo_solicitud']
        nombre = self.context['nombre']
        monto_req_min = self.context['monto_req_min']
        monto_total = self.context['monto_total']
        referencia = self.context['referencia']
        cuenta = self.context['clave']

        create_solicitud = Solicitudes.objects.create(
            nombre=nombre,
            tipoSolicitud_id=tipo_solicitud_id,
            personaSolicitud_id=persona_saldo,
            estado_id=1,
            monto_req_min=monto_req_min,
            monto_total=monto_total,
            referencia=referencia
        )

        FileResponse, DocumentId = GenerarPDFSaldos(persona_saldo, cuenta, monto_total, referencia)

        polipay_admin_and_superadmin = persona.objects.values('email', 'name', 'last_name').filter(
            Q(is_staff=True) | Q(is_superuser=True))

        list_email_admin_and_superadmin = []

        for data in polipay_admin_and_superadmin:
            data['monto_req_min'] = monto_req_min
            data['referencia'] = referencia
            data['empresa'] = persona_saldo_name
            list_email_admin_and_superadmin.append(data)

        admins_and_colaborators = grupoPersona.objects.filter(
            is_admin=True,
            empresa_id=persona_saldo
        ).values('person__email', 'person__name', 'person__last_name', 'empresa__name').filter(
            Q(relacion_grupo_id=3) | Q(relacion_grupo_id=1))

        list_email_admins_and_colaborators = []

        for data in admins_and_colaborators:
            data['monto_req_min'] = monto_req_min
            data['referencia'] = referencia
            data['clave'] = cuenta['cuentaclave']
            data['monto_total'] = monto_total
            list_email_admins_and_colaborators.append(data)

        send_massive_email(list_email_admins_and_colaborators, list_email_admin_and_superadmin)

        return DocumentId


class SerializerListSolicitudesCuentaEje(Serializer):
    comisiones = SerializerMethodField()
    solicitudes = SerializerMethodField()

    # def get_comisiones(self, obj: comisiones):
    #     instance_comision = Comisiones.objects.filter(f_persona_id=obj.empresa_id)
    #     list_comision = [j.get_comision() for j in instance_comision]
    #
    #     return list_comision

    def render_json_comission(self, **kwargs):
        type_comission = kwargs.pop('commission_rel__type')

        return {
            "id": kwargs.pop('commission_rel__servicio__product_id'),
            "producto": kwargs.pop('commission_rel__servicio__service__nombre'),
            "Porcentaje": float(kwargs.pop('commission_rel__percent') * 100),
            "Comision": True if type_comission == 1 else False
        }

    def get_comisiones(self, obj: comisiones):
        comissions = Commission.objects.select_related('person_debtor', 'person_payer', 'commission_rel').filter(
            Q(person_payer_id=obj.empresa_id) | Q(person_debtor_id=obj.empresa_id)
        ).values(
            'commission_rel__servicio__product_id',
            'commission_rel__servicio__service__nombre',
            'commission_rel__percent',
            'commission_rel__type',
        )

        return [self.render_json_comission(**comission) for comission in comissions]

    def get_solicitudes(self, obj: solicitudes):
        solicitud_instance = Solicitudes.objects.filter(personaSolicitud_id=obj.empresa_id,
                                                        tipoSolicitud_id=6).order_by('fechaSolicitud').reverse()
        lista = []

        for s in solicitud_instance:
            data = {
                'cuentaEje': obj.empresa.name,
                'Solicitudes': s.get_solicitudes_CE(),
            }
            lista.append(data)

        return lista


class SerializerAutorizarSolicitudSaldos(Serializer):
    estado_id = CharField()

    def validate(self, attrs):
        estado_id = attrs['estado_id']

        if estado_id != str(4):
            error = {'status': ['Debe autorizar la solicitud']}
            self.context.get('log').json_response(error)
            raise ValidationError(error)
        return attrs

    def update(self, instance, validated_data):
        instance.estado_id = validated_data.get('estado_id', instance.estado_id)
        instance.save()

        admins_and_colaborators = grupoPersona.objects.filter(
            is_admin=True,
            empresa_id=self.context['empresa_id']
        ).values('person__email', 'person__name', 'person__last_name', 'empresa__name').filter(
            Q(relacion_grupo_id=3) | Q(relacion_grupo_id=1))

        list_email_admins_and_colaborators = []

        for data in admins_and_colaborators:
            data['monto_req_min'] = self.context['monto_req_min']
            data['referencia'] = self.context['referencia']
            list_email_admins_and_colaborators.append(data)

        send_email_authorization(list_email_admins_and_colaborators)


class SerializerSolicitarTarjetasCuentaEjeIn(Serializer):
    # monto_total =  FloatField()
    Clasica = CharField(allow_null=False, allow_blank=False)
    Platino = CharField(allow_null=False, allow_blank=False)
    Dorada = CharField(allow_null=False, allow_blank=False)

    def validate(self, attrs):
        get_cuenta_CE = self.context['instance_cuenta_CE'].get_all_cuentas()
        monto_cuenta_eje = get_cuenta_CE['monto']
        monto_total = self.context['monto_total']
        if monto_cuenta_eje < monto_total:
            raise ValidationError({'field': 'Monto Total',
                                   'detail': 'Saldo de la cuenta eje Insuficiente',
                                   'data': f'{monto_cuenta_eje}'})
        return attrs

    def create(self, **kwargs):
        instance_cuenta_CE = self.context['instance_cuenta_CE']

        CE_solicitud = self.context['CE_solicitud']
        tipo_solicitud_id = self.context['tipo_solicitud']
        nombre_solicitud = self.context['nombre_solicitud']
        cant_clasica = self.context['cant_clasica']
        cant_platino = self.context['cant_platino']
        cant_dorada = self.context['cant_dorada']
        subtotal = self.context['monto_req_min']
        monto_total = self.context['monto_total']

        instance_solicitud = Solicitudes.objects.create(
            nombre=nombre_solicitud,
            tipoSolicitud_id=tipo_solicitud_id,
            personaSolicitud_id=CE_solicitud,
            estado_id=1,
            monto_req_min=subtotal,
            monto_total=monto_total,
            dato_json={'Clasica': cant_clasica,
                       'Platino': cant_platino,
                       'Dorada': cant_dorada}
        )
        instance_cuenta_CE.monto -= instance_solicitud.monto_total
        instance_cuenta_CE.save()

        return True


class SerializerChangeStatusToCardRequest(Serializer):
    fechaEntrega = DateField()
    edodetail_id = IntegerField()

    def validate(self, attrs):
        edo_solicitud = self.context['edo_solicitud']
        if edo_solicitud == 1 and attrs['edodetail_id'] != 5:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta solicitud necesita ser enviada'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)
        return attrs

    def create(self, **kwargs, ):
        solicitud = self.context['Solicitud']

        instance_solicitud = Detalle_solicitud.objects.create(
            sol_rel_id=solicitud,
            fechaEntrega=self.validated_data.get("fechaEntrega"),
            fechaEntregaNew=self.validated_data.get("fechaEntrega"),
            edodetail_id=self.validated_data.get("edodetail_id")
        )

        instance_solicitud.save()
        return True


class SerializerChangeStatusToCardRequestUpdate(Serializer):
    fechaEntregaNew = DateField()
    detalle = CharField(allow_blank=True)
    edodetail_id = IntegerField()

    # status:
    # 1 = Pendiente
    # 5 = En envio
    # 6 = Retraso
    # 7 = Entregada

    def validate(self, attrs):
        edo_solicitud = self.context['edo_solicitud']

        if edo_solicitud == 1 and attrs['edodetail_id'] == 1:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta Solicitud ya se encuentra pendiente'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 1 and attrs['edodetail_id'] == 7:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta Solicitud no ha sido enviada'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 5 and attrs['edodetail_id'] == 5:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta solicitud ya se encuentra en envio'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 5 and attrs['edodetail_id'] == 1:
            error = {'Code': '400', 'status': 'Error', 'message': 'Una solicitud que se encuentra en envio no puede cambiar a pendiente'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 6 and attrs['edodetail_id'] == 6:
            error =  {'Code': '400', 'status': 'Error', 'message': 'Esta solicitud ya se encuentra con retraso'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 6 and attrs['edodetail_id'] == 1:
            error = {'Code': '400', 'status': 'Error', 'message': 'Una solicitud que se encuentra con retraso no puede cambiar a pendiente'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 6 and attrs['edodetail_id'] == 5:
            error = {'Code': '400', 'status': 'Error','message': 'Esta solicitud ya ha sido enviada pero se ha retrasado la fecha de entrega'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 7 and attrs['edodetail_id'] != 7:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta solicitud ya ha sido entregada'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if edo_solicitud == 7 and attrs['edodetail_id'] == 7:
            error = {'Code': '400', 'status': 'Error', 'message': 'Esta solicitud ya ha sido entregada'}
            self.context.get('log').json_response(error)
            raise ValidationError(error)
        return attrs

    def update(self, instance, validated_data):
        instance.fechaEntregaNew = validated_data.get('fechaEntregaNew', instance.fechaEntregaNew)
        instance.detalle = validated_data.get('detalle', instance.detalle)
        instance.edodetail_id = validated_data.get('edodetail_id', instance.edodetail_id)
        instance.save()


# (AAF 2021-12-14) creacion de solicitudes genericas
class SerializerCreateSol(Serializer):
    nombre = CharField()
    tipoSolicitud_id = IntegerField()
    personaSolicitud_id = IntegerField()
    fechaSolicitud = DateTimeField(default=datetime.datetime.now())
    estado_id = IntegerField(default=1)
    intentos = IntegerField(default=0)
    monto_req_min = FloatField(default=None)
    monto_total = FloatField(default=None)
    dato_json = CharField(default=None)
    referencia = JSONField(default=None)

    def create(self, validated_data):
        try:
            instance = Solicitudes.objects.create(**validated_data)
        except Exception as ex:
            print(ex)
            return False
        return instance


class SerializerRequestCardsCostCenter(Serializer):
    Clasica = IntegerField(allow_null=False)
    Platino = IntegerField(allow_null=False)
    Dorada = IntegerField(allow_null=False)

    def create(self, validated_data):
        cards_clasicas = validated_data.get('Clasica')
        cards_platino = validated_data.get('Platino')
        cards_doarada = validated_data.get('Dorada')

        payload = {
            'Clasica': cards_clasicas,
            'Platino': cards_platino,
            'Dorada': cards_doarada,
            'Colaborador': self.context['colaborador']
        }

        instances_solicitud = Solicitudes.objects.create(
            nombre='Solicitud Tarjetas Centro Costos',
            tipoSolicitud_id=9,
            personaSolicitud_id=self.context['personaSolicitud_id'],
            estado_id=1,
            dato_json=json.dumps(payload)
        )
        return instances_solicitud


class SerializerCancelCardsRequest(Serializer):

    def validate(self, attrs):
        list_errors = ErrorsList()
        list_errors.clear_list()
        status_request_id = self.context['status_request']

        if status_request_id == 11:
            ErrorsList("Request", message='Esta solictud de tarjetas ya ha sido entregada')

        if status_request_id == 10:
            ErrorsList("Request", message='Esta solicitud ya ha sido cancelada')

        if list_errors.len_list_errors() > 0:
            self.context.get('log').json_response(list_errors.standard_error_responses())
            raise ValidationError(list_errors.standard_error_responses())

        list_errors.clear_list()
        return attrs

    def update(self, instance, validated_data):
        instance.estado_id = 10
        instance.save()


class SerializerAssingCardsCostCenter(Serializer):
    Clasicas = ListField(allow_empty=True)
    Platino = ListField(allow_empty=True)
    Doradas = ListField(allow_empty=True)

    def validate(self, attrs):
        list_errors = ErrorsList()
        list_errors.clear_list()

        get_classics_cards = tarjeta.objects.filter(clientePrincipal_id=self.context['company_id'], status="04",
                                                    tipo_tarjeta_id=1)
        # get_platinum_cards = tarjeta.objects.filter(clientePrincipal_id=self.context['company_id'], status="04",
        #                                             tipo_tarjeta_id=2)
        # get_golden_cards = tarjeta.objects.filter(clientePrincipal_id=self.context['company_id'], status="04",
        #                                           tipo_tarjeta_id=3)
        request = Solicitudes.objects.get(id=self.context['request_id'])

        if request.estado_id == 11:
            ErrorsList("Request", message="Esta solicitud de tarjetas ya ha sido asignada anteriormente")

        if len(attrs['Clasicas']) > len(get_classics_cards):
            ErrorsList("Classics Cards", message='No cuentas con stock suficiente para asignar tarjetas',
                       value=str(len(get_classics_cards)))

        # if len(attrs['Platino']) > len(get_platinum_cards):
        #     ErrorsList("Platinum Cards", message='No cuentas con stock suficiente para asignar tarjetas',
        #                value=str(len(get_platinum_cards)))
        #
        # if len(attrs['Doradas']) > len(get_golden_cards):
        #     ErrorsList("Golden Cards", message='No cuentas con stock suficiente para asignar tarjetas',
        #                value=str(len(get_golden_cards)))

        if list_errors.len_list_errors() > 0:
            self.context('log').json_response(list_errors.standard_error_responses())
            raise ValidationError(list_errors.standard_error_responses())

        list_errors.clear_list()
        return attrs

    def update(self, instance, validated_data):
        try:
            with atomic():
                request_id = self.context['request_id']
                cliente_principal = self.context['cost_center_id']
                tarjeta_clasica_id = self.validated_data.get('Clasicas')
                tarjetas_platino_id = self.validated_data.get('Platino')
                tarjetas_doradas_id = self.validated_data.get('Doradas')

                list_cards_classics = []
                list_cards_platinum = []
                list_card_golden = []

                for tarjetas_clasicas in tarjeta_clasica_id:
                    instance_tarjeta = tarjeta.objects.get(id=tarjetas_clasicas, tipo_tarjeta_id=1,
                                                           clientePrincipal_id=self.context['company_id'])

                    instance_tarjeta.status = "00"
                    instance_tarjeta.clientePrincipal_id = self.context['cost_center_id']
                    instance_tarjeta.cuenta_id = self.context['get_account']
                    instance_tarjeta.save()
                    list_cards_classics.append(tarjetas_clasicas)

                for tarjetas_platino in tarjetas_platino_id:
                    instance = tarjeta.objects.get(id=tarjetas_platino, tipo_tarjeta_id=2,
                                                   clientePrincipal_id=self.context['company_id'])
                    instance.status = "00"
                    instance.clientePrincipal_id = self.context['cost_center_id']
                    instance.cuenta_id = self.context['get_account']
                    instance.save()
                    list_cards_platinum.append(tarjetas_platino)

                for tarjetas_doradas in tarjetas_doradas_id:
                    instance = tarjeta.objects.get(id=tarjetas_doradas, tipo_tarjeta_id=3,
                                                   clientePrincipal_id=self.context['company_id'])
                    instance.status = "00"
                    instance.clientePrincipal_id = self.context['cost_center_id']
                    instance.cuenta_id = self.context['get_account']
                    instance.save()
                    list_card_golden.append(tarjetas_doradas)

                changueStatusRequest(request_id, cliente_principal)

                return list_cards_classics, list_cards_platinum, list_card_golden
        except IntegrityError as e:
            error = {'code': 400, 'status': 'error', 'message': 'Ocurrio un error inesperado al momento de asignar las tarjetas', 'detail': str(e)}
            self.context('log').json_response(error)
            raise ValidationError(error)
