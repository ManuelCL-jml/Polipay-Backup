# import random
# import string
import datetime

from rest_framework.serializers import *
from rest_framework import serializers

from apps.transaction.models import tipo_transferencia, bancos
from polipaynewConfig.inntec import AsignarTarjetaPersonaExternaInntec
# from MANAGEMENT.Utils.utils import random_password
# from apps.users.models import persona
# from apps.users.management import generate_password, filter_object_if_exist
from apps import solicitudes
from apps.solicitudes.management import AceptarSolicitud, DevolverSolicitud, changeStatusRequest
from apps.solicitudes.models import Solicitudes
from apps.users.models import persona, domicilio, documentos, tarjeta, cuenta, grupoPersona
from polipaynewConfig.exceptions import MensajeError
from polipaynewConfig.inntec import SepararApellidos, ClaveEmpleado
from polipaynewConfig.settings import STATIC_URL, rfc_Bec


class client_data_in(serializers.Serializer):
    centro_costos_id = serializers.IntegerField(required=True, allow_null=False)
    client_name = serializers.CharField(default=None)
    estado = serializers.CharField(default=None)
    cuenta = serializers.CharField(default=None)
    clabe = serializers.CharField(default=None)
    fecha_inicio = serializers.CharField(default=None)
    fecha_fin = serializers.CharField(default=None)


class SerializerAPIclientList(serializers.Serializer):
    id_persona_CC = serializers.IntegerField()
    id_tabla_solicitud = serializers.IntegerField()
    cliente = serializers.CharField()
    estado = serializers.CharField()
    cuenta = serializers.CharField()
    clabe = serializers.CharField()
    fecha_captura = serializers.DateTimeField()
    tipo_cliente = serializers.IntegerField()


class SerializerSolclientList(serializers.Serializer):
    id_sol = serializers.IntegerField()
    intentos = serializers.IntegerField()
    id_cliente = serializers.IntegerField()
    cliente = serializers.CharField()
    tipo = serializers.CharField()
    estado = serializers.CharField()
    fecha = serializers.DateTimeField()
    t_persona = serializers.IntegerField()


class SerializerAuthorizeCE(Serializer):
    ce_id = ReadOnlyField()


class SerializerNotificacionCE(Serializer):
    centro_id = ReadOnlyField()


class DismissSoli(Serializer):
    idCE = serializers.IntegerField()
    idPersonaSol = serializers.IntegerField()
    idSol = serializers.IntegerField()
    state = serializers.BooleanField()

    def update(self, instance, validated_data):
        clientE = persona.objects.get(id=validated_data['idCE'])
        if validated_data['state'] == True:
            AceptarSolicitud(instance["id"], validated_data['idPersonaSol'])
            # changeStatusRequest(instance["id"], validated_data['idCE'], validated_data["idPersonaSol"], 4, "")
            clientE.state = False
        else:
            clientE.state = True
            DevolverSolicitud(instance["id"], validated_data['idCE'])
        clientE.save()
        return instance["id"]


class SolicitudesOut(Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    curp = serializers.CharField()
    clave_traspaso = serializers.CharField()
    banco_clabe = serializers.CharField()
    domicilio = serializers.SerializerMethodField()
    idSolicitud = serializers.SerializerMethodField()
    docto = serializers.SerializerMethodField()

    def get_domicilio(self, obj: domicilio):
        # queryset = domicilio.objects.get(domicilioPersona=obj.id)
        dom = domicilio.objects.values('codigopostal', 'colonia', 'alcaldia_mpio', 'estado', 'calle',
                                       'no_exterior', 'no_interior', 'pais').get(domicilioPersona_id=obj.id,
                                                                                 historial=False)
        return dom

    def get_idSolicitud(self, obj: idSolicitud):
        sol = Solicitudes.objects.filter(personaSolicitud_id=str(obj.id))
        list_sol = {}
        list_sol["id_Sol"] = sol[0].id
        list_sol["motivo"] = sol[0].nombre
        return list_sol

    def get_docto(self, obj: docto):
        document = documentos.objects.filter(person_id=obj.id, tdocumento_id=19, historial=False)
        list_doc = {}
        list_doc["id_docto"] = document[0].id
        list_doc["comentario"] = document[0].comentario
        url = STATIC_URL + str(document[0].documento)
        list_doc["documento"] = url.replace("static", "media")
        list_doc["status"] = document[0].status
        return list_doc


class SerializerVerifyDocumentsClienteExterno(Serializer):
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


class SerializerAsignarTarjetaClienteExterno(Serializer):
    Tarjeta = ListField()

    def validate_tarjeta(self, data, company_id, cost_center_id, account_number):
        error = []
        usuario = cuenta.objects.get(cuenta=account_number)

        if not grupoPersona.objects.filter(empresa_id=company_id, person_id=cost_center_id, relacion_grupo_id=5):
            error.append({"field": "null", "data": "null",
                          "message": "No se encontro la relacion de la cuenta eje con el centro de costos"})

        if not grupoPersona.objects.filter(empresa_id=cost_center_id, person_id=usuario.persona_cuenta_id,
                                           relacion_grupo_id=9):
            error.append({"field": "null", "data": "null",
                          "message": "No se encontro la relacion del centro de costos con el cliente externo"})
        for i in data:
            if tarjeta.objects.filter(tarjeta=i, status="00"):
                error.append({"field": "null", "data": i, "message": "Tarjeta ya registrada"})

            if not tarjeta.objects.filter(tarjeta=i, clientePrincipal_id=company_id):
                error.append({"field": "null", "data": i, "message": "Tarjeta no encontrada en la cuenta eje"})

        MensajeError(error)
        return data

    def update(self, instance_cuenta, instance_persona, type):
        numerotarjeta = self.validated_data.get("Tarjeta")
        lista = []
        if type in ["Produccion", "Pruebas"]:
            for numero_tarjeta in numerotarjeta:
                instanceTarjeta = tarjeta.objects.get(tarjeta=numero_tarjeta)
                apellidos = SepararApellidos(instance_persona)

                if apellidos[0] == "" or apellidos[0] == None:
                    apellido_paterno = "NA"
                else:
                    apellido_paterno = apellidos[0]
                if apellidos[1] == "" or apellidos[1] == None:
                    apellido_materno = "NA"
                else:
                    apellido_materno = apellidos[1]
                if instanceTarjeta.ClaveEmpleado == "" or instanceTarjeta.ClaveEmpleado == None:
                    nueva_clave = ClaveEmpleado()
                    instanceTarjeta.ClaveEmpleado = nueva_clave
                    instanceTarjeta.save()

                if instance_persona.rfc == "" or instance_persona.rfc == None:
                    rfc = rfc_Bec
                else:
                    rfc = instance_persona.rfc

                diccionario = [
                    {
                        "TarjetaId": instanceTarjeta.TarjetaId,
                        "ClienteId": "C000682",  # C000682 ----> Produccion, C000022 -----> Pruebas
                        "ProductoId": 56,
                        "Nombre": instance_persona.name,
                        "ApellidoPaterno": apellido_paterno,
                        "ApellidoMaterno": apellido_materno,
                        "NombreCorto": "",
                        "RFC": rfc,
                        "CURP": "",
                        "NSS": "",
                        "Direccion": "",
                        "NumeroTelefonoMovil": "9999999999",
                        "NumeroTelefonoCasa": "9999999999",
                        "NumeroTelefonoTrabajo": "",
                        "Estado": "",
                        "Municipio": "",
                        "Ciudad": "",
                        "Colonia": "",
                        "CorreoElectronico": instance_persona.email,
                        "CodigoPostal": "",
                        "MontoInicial": "0.0",
                        "ClaveEstado": "",
                        "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
                        "CodigoRetenedora": ""
                    }
                ]
                if type == "Produccion":
                    AsignarTarjetaPersonaExternaInntec(diccionario)  # Produccion
                instanceTarjeta.status = "00"
                instanceTarjeta.is_active = True
                instanceTarjeta.cuenta_id = instance_cuenta.id
                instanceTarjeta.save()
                lista.append(numero_tarjeta)
                return lista
        else:
            error = [{'field': 'null', "data": 'null', 'message': "Tipo no identificado"}]
            MensajeError(error)


class SerializerMovimentDetailsExternClient(Serializer):
    id = serializers.CharField()
    concepto_pago = serializers.CharField()
    fecha_creacion = serializers.DateTimeField()
    monto = serializers.FloatField()
    cuenta_emisor = serializers.CharField()
    nombre_emisor = serializers.CharField()
    transmitter_bank_id = serializers.SerializerMethodField()
    cta_beneficiario = serializers.IntegerField()
    nombre_beneficiario = serializers.ReadOnlyField()
    receiving_bank_id = serializers.SerializerMethodField()
    referencia_numerica = serializers.IntegerField()


    def get_receiving_bank_id(self, obj: receiving_bank_id):
        banks = bancos.objects.filter(id=obj.receiving_bank_id).values('institucion').first()
        if banks:
            return banks.get('institucion')
        return None

    def get_transmitter_bank_id(self, obj: transmitter_bank_id):
        banks = bancos.objects.filter(id=obj.transmitter_bank_id).values('institucion').first()
        if banks:
            return banks.get('institucion')
        return None