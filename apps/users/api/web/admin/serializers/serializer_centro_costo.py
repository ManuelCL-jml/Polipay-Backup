import datetime
from rest_framework.serializers import *
from drf_extra_fields.fields import Base64FileField

# from apps.users.models import cuenta, persona, TDocumento, domicilio
from apps.transaction.models import bancos
# from apps.solicitudes.models import *
from apps.users.management import *


# - - - - - - S e r i a l i z a d o r e s   P r i n c i p a l e s - - - - - -

class SerializerDeleteCentroCostoAdmin(Serializer):
    """
    Dar de baja centro de costos del lado de administrador

    """

    motivo = CharField(allow_null=True, allow_blank=True)

    def validate(self, attrs):
        centro_costos_id = self.context['instance_grupo_persona']['empresa_id']
        doc = filter_data_or_return_none(documentos, tdocumento_id=15, person_id=centro_costos_id)

        if not doc.is_authorization():
            raise ValidationError({'status': ['El documento aun no puede ser dado de baja']})

        return attrs

    def update(self, **kwargs):
        centro_costos_id = self.context['instance_grupo_persona']["empresa_id"]
        representante_legal_id = self.context['instance_grupo_persona']["person_id"]

        persona.objects.filter(
            pk=centro_costos_id).update(
            state=False,
            motivo=self.validated_data['motivo'],
            is_active=False
        )

        persona.objects.filter(
            pk=representante_legal_id).update(
            state=False,
            motivo=self.validated_data['motivo'],
            is_active=False
        )

        instance_clabe = filter_data_or_return_none(cuenta, persona_cuenta_id=centro_costos_id)

        instance_clabe.expire = get_timedelta(days=182, minutes=0)
        instance_clabe.is_active = False
        instance_clabe.save()

        get_Object_orList_error(Solicitudes, tipoSolicitud_id=2, personaSolicitud_id=centro_costos_id).delete()
        return True


""" - - - - - - S e r i a l i z a d o r e s   d e   L i s t a d o - - - - - - """


class SerializerListarSolicitudesCentroCostos(Serializer):
    # solicitudes = CharField()

    def to_representation(self, instance):
        lista = {
            'idCC': instance.personaSolicitud.id,
            'Centro_Costos': instance.personaSolicitud.name,
            'tipo_solicitud': instance.tipoSolicitud.nombreSol,
            'fecha_Sol': instance.fechaSolicitud,
            'intentos': instance.intentos,
            'estado': instance.estado.nombreEdo,
            'idSol': instance.id
        }
        return lista


class SerialiazerListarCentroCostosActivos(Serializer):
    def to_representation(self, instance):
        return {
            'Centro_Costos': instance.person.get_centro_costo(),
            'cuentas': cuenta.objects.values('id', 'cuenta', 'cuentaclave', 'is_active', 'monto').filter(
                persona_cuenta_id=instance.person_id)
        }


class DocumentsIn(Serializer):
    id = IntegerField()
    status = CharField(allow_null=False, allow_blank=False)
    comentario = CharField(allow_null=True, allow_blank=True)


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


class SerializerSolicitudAperturaCentroCostosOut(Serializer):
    id = ReadOnlyField()
    last_name = CharField()
    rfc = CharField()
    RepresentanteLegal = SerializerMethodField()
    DomicilioFiscal = SerializerMethodField()
    DatosTransferenciaFinal = SerializerMethodField()
    banco_clabe = SerializerMethodField()
    documents = SerializerMethodField()

    def get_DomicilioFiscal(self, obj: DomicilioFiscal):
        queryGP = grupoPersona.objects.get(empresa_id=obj.id, relacion_grupo_id=4)
        queryPL = persona.objects.get(id=queryGP.person_id)
        instance = domicilio.objects.filter(domicilioPersona_id=queryPL.id)
        return SerializerAddressOut(instance, many=True).data

    def get_banco_clabe(self, obj: banco_clabe):
        instance_banco = get_Object_orList_error(bancos, clabe=obj.banco_clabe)
        return {
            'banco': instance_banco.institucion
        }

    def get_DatosTransferenciaFinal(self, obj: DatosTransferenciaFinal):
        queryset = persona.objects.get(id=obj.id)
        return {
            'clave_traspaso': queryset.clave_traspaso
        }

    def get_RepresentanteLegal(self, obj: RepresentanteLegal):
        queryset = get_Object_orList_error(grupoPersona, relacion_grupo=4, empresa_id=obj.id)
        datos = []
        for data in queryset:
            instance = persona.objects.get(id=data.person_id)
            datos.append(instance)
        return SerializerRepresentanteLegal(datos, many=True).data

    def get_documents(self, obj: documents):
        queryset = documentos.objects.filter(person_id=obj.id)
        return SerializerDocumentsOut(queryset, many=True).data


class SerializerAuthorizeManyIn(Serializer):
    documents_representante = DocumentsIn(many=True, allow_null=True)
    documents_razon_social = DocumentsIn(many=True, allow_null=True)

    def validate_documents_representante(self, data):
        for document in data:
            if document["status"] == "P" or document["status"] == "D" or document["status"] == "C":
                continue
            raise ValidationError({'status': ['Estado de documento no reconocido']})
        return data

    def validate_documents_razon_social(self, data):
        for document in data:
            if document["status"] == "P" or document["status"] == "D" or document["status"] == "C":
                continue
            raise ValidationError({'status': ['Estado de documento no reconocido']})
        return data


class SerializerAuthorizeCentroCosto(SerializerAuthorizeManyIn):
    def auth_document(self, list_document: list, user_id: int):
        n_documento_devuelto = 0
        person_id = 0

        for document in list_document:
            data = documentos.objects.filter(pk=document.get('id')).values('status', 'person_id')
            data.update(comentario=document.get('comentario'), status=document.get('status'))

            person_id = data[0].get('person_id')
            if data[0].get('status') == "C" or data[0].get('status') == 'D':
                data.update(authorization=True, dateauth=datetime.datetime.now(), userauth_id=user_id)

            if data[0].get('status') == "C":
                n_documento_devuelto += 1

        return n_documento_devuelto, person_id

    def delete_solicitud(self, centro_costos_id):
        solicitud = Solicitudes.objects.filter(personaSolicitud_id=centro_costos_id)
        if solicitud:
            solicitud.delete()
        return None

    def create_account(self, new_cuentaclave, centro_costos_id):
        """ Creamos una cuenta para centro de costos """
        cuenta.objects.create(
            cuenta=get_account(new_cuentaclave),
            is_active=True,
            persona_cuenta_id=centro_costos_id,
            cuentaclave=new_cuentaclave
        )

    def activate_centro_costo(self, centro_costos_id):
        centro_costo = persona.objects.filter(id=centro_costos_id).values('is_active')
        centro_costo.update(is_active=True)
        return True

    def activate_centro_costos(self, centro_costo_id: int):
        cuenta_eje = get_Object_orList_error(grupoPersona, person_id=centro_costo_id).get_person_and_empresa()
        new_cuentaclave, ivalid = generate_cuentaclave(cuenta_eje['empresa_id'])

        if ivalid:
            raise ValidationError({'status': ['Se llego al limite de clabes interbancarias']})

        self.create_account(new_cuentaclave=new_cuentaclave, centro_costos_id=centro_costo_id)
        self.activate_centro_costo(centro_costos_id=cuenta_eje['person_id'])
        self.delete_solicitud(centro_costos_id=centro_costo_id)

    def auth_all_documents(self, pk_user):
        list_documents_representante = self.validated_data.pop("documents_representante")
        list_documents_razon_social = self.validated_data.pop("documents_razon_social")

        centro_costo, centro_costo_id = self.auth_document(list_documents_razon_social, pk_user)
        r_legal, _ = self.auth_document(list_documents_representante, pk_user)

        if len(list_documents_razon_social) == centro_costo and len(list_documents_representante) == r_legal:
            self.activate_centro_costos(centro_costo_id)
            return True

        return False


class SerializerAuthorizeBaja(Serializer):
    document_motivo_baja = DocumentsIn()
    motivo_baja = CharField(allow_null=True, allow_blank=True)

    def validate_document_motivo_baja(self, data):
        auth_doc = ['P', 'D', 'C']

        if data.get('status') in auth_doc:
            return data
        raise ValidationError({'status': ['Estado de documento no reconocido']})

    def delete_solicitud(self, centro_costos_id):
        solicitud = Solicitudes.objects.filter(personaSolicitud_id=centro_costos_id)
        if solicitud:
            solicitud.delete()
        return None

    def baja_centro_costo(self, centro_costo_id, motivo_baja):
        centro_costo = persona.objects.filter(pk=centro_costo_id)
        centro_costo.update(state=False, is_active=False, motivo=motivo_baja)

    def update_status_document(self, **kwargs):
        data = kwargs.get('document')
        change_status = ['C', 'D']

        document = documentos.objects.filter(id=data.get('id')).values('status', 'person_id')
        document.update(comentario=data.get('comentario'), status=data.get('status'))
        centro_costo_id = document[0].get('person_id')

        if data.get('status') in change_status:
            data.update(authorization=True, dateauth=datetime.datetime.now(), userauth_id=kwargs.get('user_id'))
            return centro_costo_id, data.get('status')

        return centro_costo_id, data.get('status')

    def auth_all_documents(self, pk_user):
        document_motivo_baja = self.validated_data.get("document_motivo_baja")
        motivo_baja = self.validated_data.get("motivo_baja")

        centro_costo_id, status = self.update_status_document(
            document=document_motivo_baja,
            user_id=pk_user,
            motivo_baja=motivo_baja
        )

        if status == 'C':
            self.baja_centro_costo(centro_costo_id, motivo_baja)
            self.delete_solicitud(centro_costos_id=centro_costo_id)

        return False


class SerializerDocumentsOut(Serializer):
    id = ReadOnlyField()
    documento = FileField()
    TipoDocumento = SerializerMethodField()

    def get_TipoDocumento(self, obj: TipoDocumento):
        queryset = TDocumento.objects.filter(id=obj.tdocumento_id)
        return SerializerTDocumentoOut(queryset, many=True).data


class SerializerTDocumentoOut(Serializer):
    id = ReadOnlyField()
    nombreTipo = CharField()


class SerializerRepresentanteLegal(Serializer):
    id = ReadOnlyField()
    name = SerializerMethodField()
    email = CharField()
    rfc = CharField()
    documents = SerializerMethodField()

    def get_name(self, obj: name):
        return obj.get_full_name()

    def get_documents(self, obj: documents):
        queryset = documentos.objects.filter(person_id=obj.id)
        return SerializerDocumentsOut(queryset, many=True).data


class SerializerDocumento(Serializer):
    id = ReadOnlyField()
    documento = Base64FileField()
    status = CharField()
    comentario = CharField()
    tdocumento_id = IntegerField()


class SerializerDocumentosResultadosOut(Serializer):
    centroCostoDetail = SerializerMethodField()
    representanteDetail = SerializerMethodField()
    documentos_centro_costos = SerializerMethodField()
    documento_representante = SerializerMethodField()

    def get_documentos_centro_costos(self, obj: documentos_centro_costos):
        queryset = documentos.objects.filter(person_id=obj.empresa_id)
        return SerializerDocumento(queryset, many=True).data

    def get_documento_representante(self, obj: documento_representante):
        queryset = documentos.objects.filter(person_id=obj.person_id)
        return SerializerDocumento(queryset, many=True).data

    def get_centroCostoDetail(self, obj: centroCostoDetail):
        queryset = persona.objects.values(
            'id',
            'name',
            'last_name',
            'rfc',
            'clave_traspaso',
            'banco_clabe'
        ).get(id=obj.empresa_id)

        domicilio_CC = domicilio.objects.values(
            'codigopostal',
            'colonia',
            'alcaldia_mpio',
            'estado',
            'calle',
            'no_exterior',
            'no_interior',
            'pais'
        ).filter(domicilioPersona_id=obj.empresa_id, historial=False)

        data = []
        data.append(queryset)
        for dom in domicilio_CC:
            data.append(dom)
        return data

    def get_representanteDetail(self, obj: representanteDetail):
        queryset = persona.objects.values('id', 'name', 'last_name', 'rfc', 'phone', 'email').filter(id=obj.person_id)
        domicilio_Rep = domicilio.objects.values('codigopostal', 'colonia', 'alcaldia_mpio', 'estado', 'calle',
                                                 'no_exterior', 'no_interior', 'pais').filter(
            domicilioPersona_id=obj.person_id, historial=False)
        data = []
        for query in queryset:
            data.append(query)
        for dom in domicilio_Rep:
            data.append(dom)
        return data


class SerializerAuthorizeCenter(Serializer):
    centro_id = ReadOnlyField()


class SerializerNotificacionCentro(Serializer):
    centro_id = ReadOnlyField()


class DocumentsUpdate(Serializer):
    id = IntegerField()
    status = CharField(required=False)
    comentario = CharField(required=False, allow_null=True, allow_blank=True)
    documento = FileField(required=False)

    # (AAF 2021-12-10) se añade id persona autorizacion al autorizar documentos
    def update(self, instance, validated_data, idauth):
        if 'status' in validated_data:
            instance.status = validated_data['status']
        if 'comentario' in validated_data:
            instance.comentario = validated_data['comentario']
        if 'documento' in validated_data:
            instance.documento = validated_data['documento']
        # print(instance.id)
        instance.dateauth = datetime.datetime.today()
        instance.userauth_id = idauth
        instance.dateupdate = datetime.datetime.today()  # al autorizar unicamente fecha de autorizacion
        instance.save()
        return instance


class DetailsCostCenter(Serializer):
    id = IntegerField()
    status = CharField()
    comentario = CharField()
    tipo_documento = SerializerMethodField()
    documento = SerializerMethodField()

    def get_tipo_documento(self, obj: tipo_documento):
        queryset = TDocumento.objects.filter(id=obj.tdocumento_id).values('id', 'nombreTipo')
        return queryset

    def get_documento(self, obj: documento):
        queryset = obj.get_url_aws_document()
        return queryset


class SerializerDetailsCostCenter(Serializer):
    RazonSocial = serializers.SerializerMethodField()
    RepresentanteLegal = serializers.SerializerMethodField()

    def get_RazonSocial(self, obj: RazonSocial):
        person_instance = persona.objects.get(id=obj.empresa_id)
        # bank_instance = bancos.objects.get(clabe=person_instance.banco_clabe)
        domicilio_instance = domicilio.objects.filter(domicilioPersona_id=person_instance).last()

        doc = documentos.objects.filter(person_id=person_instance, historial=0)
        serializer = DetailsCostCenter(instance=doc, many=True)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.name,
            "RazonSocial": person_instance.last_name,
            "Rfc": person_instance.rfc,
            # "ClaveTraspasoFinal": person_instance.clave_traspaso,
            # "Banco": bank_instance.institucion,
            "DomicilioFiscal": None if domicilio_instance is None else domicilio_instance.get_domicilio(),
            "Documentos": serializer.data
        }

    def get_RepresentanteLegal(self, obj: RepresentanteLegal):
        person_instance = persona.objects.get(id=obj.person_id)
        domicilio_instance = domicilio.objects.filter(domicilioPersona_id=person_instance.id).last()

        doc = documentos.objects.filter(person_id=person_instance.id, historial=0)
        serializer = DetailsCostCenter(instance=doc, many=True)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.get_name_company(),
            "Apellido": person_instance.get_last_name(),
            "FechaNacimiento": person_instance.fecha_nacimiento,
            "CorreoElectronico": person_instance.email,
            "Rfc": person_instance.rfc,
            "Domicilio": None if domicilio_instance is None else domicilio_instance.get_domicilio(),
            "Phone": person_instance.phone,
            "Documentos": serializer.data
        }


class SerializerConsultarCentroCostos(Serializer):
    RazonSocial = serializers.SerializerMethodField()
    RepresentanteLegal = serializers.SerializerMethodField()

    def get_RazonSocial(self, obj: RazonSocial):
        person_instance = persona.objects.get(id=obj.empresa_id)
        bank_instance = bancos.objects.get(clabe=person_instance.banco_clabe)
        domicilio_instance = domicilio.objects.get(domicilioPersona_id=person_instance)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.name,
            "Rfc": person_instance.rfc,
            "ClaveTraspasoFinal": person_instance.clave_traspaso,
            "Banco": bank_instance.institucion,
            "NumeroTresDigitos": person_instance.banco_clabe,
            "DomicilioFiscal": domicilio_instance.get_domicilio(),
        }

    def get_RepresentanteLegal(self, obj: RepresentanteLegal):
        person_instance = persona.objects.get(id=obj.person_id)

        return {
            "Nombre": person_instance.get_full_name(),
            "CorreoElectronico": person_instance.email,
            "Telefono": person_instance.phone
        }


class SerializerBajaCostCenter(Serializer):
    RazonSocial = serializers.SerializerMethodField()

    def get_RazonSocial(self, obj: RazonSocial):
        person_instance = persona.objects.get(id=obj.empresa_id)
        bank_instance = bancos.objects.get(clabe=person_instance.banco_clabe)
        domicilio_instance = domicilio.objects.get(domicilioPersona_id=person_instance)

        doc = documentos.objects.filter(person_id=person_instance, historial=0).filter(
            Q(tdocumento_id=15) | Q(tdocumento_id=14))
        serializer = DetailsCostCenter(instance=doc, many=True)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.name,
            "Rfc": person_instance.rfc,
            "ClaveTraspasoFinal": person_instance.clave_traspaso,
            "Banco": bank_instance.institucion,
            "NumeroTresDigitos": person_instance.banco_clabe,
            "DomicilioFiscal": domicilio_instance.get_domicilio(),
            "Documentos": serializer.data
        }


class SerializerClaveTraspasoFinalCostCenter(Serializer):
    RazonSocial = serializers.SerializerMethodField()

    def get_RazonSocial(self, obj: RazonSocial):
        person_instance = persona.objects.get(id=obj.empresa_id)
        bank_instance = bancos.objects.get(clabe=person_instance.banco_clabe)
        domicilio_instance = domicilio.objects.get(domicilioPersona_id=person_instance)

        doc = documentos.objects.filter(person_id=person_instance, historial=0).filter(tdocumento_id__in=[5, 8],
                                                                                       status='P')
        serializer = DetailsCostCenter(instance=doc, many=True)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.name,
            "Rfc": person_instance.rfc,
            "ClaveTraspasoFinal": person_instance.clave_traspaso,
            "Banco": bank_instance.institucion,
            "NumeroTresDigitos": person_instance.banco_clabe,
            "DomicilioFiscal": domicilio_instance.get_domicilio(),
            "Documentos": serializer.data
        }


class SerializerDomicilioFiscalCostCenter(Serializer):
    RazonSocial = serializers.SerializerMethodField()

    def get_RazonSocial(self, obj: RazonSocial):
        person_instance = persona.objects.get(id=obj.empresa_id)
        bank_instance = bancos.objects.get(clabe=person_instance.banco_clabe)
        domicilio_instance = domicilio.objects.get(domicilioPersona_id=person_instance)

        doc = documentos.objects.filter(person_id=person_instance, historial=0).filter(tdocumento_id=6, status='P')
        serializer = DetailsCostCenter(instance=doc, many=True)

        return {
            "id": person_instance.id,
            "Nombre": person_instance.name,
            "Rfc": person_instance.rfc,
            "ClaveTraspasoFinal": person_instance.clave_traspaso,
            "Banco": bank_instance.institucion,
            "NumeroTresDigitos": person_instance.banco_clabe,
            "DomicilioFiscal": domicilio_instance.get_domicilio(),
            "Documentos": serializer.data
        }


class SerializerVerifyDocumentsCostCenter(Serializer):
    document_id = IntegerField()
    status = CharField()
    comment = CharField(allow_null=True)

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        documentos.objects.update_document(
            document_id=self.validated_data.get('document_id'),
            user_auth=self.context.get('user_auth'),
            status=self.validated_data.get('status'),
            comment=self.validated_data.get('comment'),
            person_id=self.context.get('representante_id')
        )


class SerializerVerifyDocumentsCostCenterNew(Serializer):
    document_id = IntegerField()
    status = CharField()
    comment = CharField(allow_null=True)

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        documentos.objects.update_document(
            document_id=self.validated_data.get('document_id'),
            user_auth=self.context.get('user_auth'),
            status=self.validated_data.get('status'),
            comment=self.validated_data.get('comment')
        )


class SerializerVerifyDocumentsClaveTraspaso(Serializer):
    document_id = IntegerField()
    status = CharField()
    comment = CharField(allow_null=True)

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        documentos.objects.update_document(
            document_id=self.validated_data.get('document_id'),
            user_auth=self.context.get('user_auth'),
            status=self.validated_data.get('status'),
            comment=self.validated_data.get('comment'),
        )


class SerializerVerifyDocumentsDomicilioFiscal(Serializer):
    document_id = IntegerField()
    status = CharField()
    comment = CharField(allow_null=True)

    def validate(self, attrs):
        return attrs

    def update(self, **kwargs):
        documentos.objects.update_document(
            document_id=self.validated_data.get('document_id'),
            user_auth=self.context.get('user_auth'),
            status=self.validated_data.get('status'),
            comment=self.validated_data.get('comment'),
        )
