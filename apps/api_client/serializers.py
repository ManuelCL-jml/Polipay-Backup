import datetime
from os import remove
from django.db.models import Q
from typing import List, Dict

from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldDoesNotExist
from django.core.files import File
from django.db.transaction import atomic

from polipaynewConfig.exceptions import ErrorsList, MensajeError
from apps.solicitudes.models import *
from apps.users.models import *
from apps.transaction.models import *
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from apps.contacts.models import contactos
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig

from .models import *
from .messages import createWelcomeMessageExternalPerson, createMessageTransactionSend
from .inntecFunctions import tipo_movimiento, get_historial, AsignarTarjetaPersonaExternaInntec, AsignarTarjetaPersonaExternaInntecPrueba, separar_apellidos, \
    clave_empleado,ClaveEmpleadoPrueba, listCard, listCardPrueba, create_disper, get_Saldo, get_status, get_token_test, get_CardsStockMasivoPrueba,\
    ClaveEmpleadoMasivoPrueba,listCardMasivoPrueba
from .management import generar_username, persona_externa_grupopersona, order_cuenta, create_file, \
    get_Object_orList_error
from .sms import enviarSMS


class SerializerAPIRequestIn(serializers.Serializer):
    def create(self, **kwargs):
        create_solicitud = Solicitudes.objects.create(
            nombre=self.context['nombre'],
            estado_id=1,
            personaSolicitud_id=self.context['cuenta_eje'],
            tipoSolicitud_id=self.context['tipo_solicitud'],
        )
        return True


class SerializerListAPIRequest(serializers.Serializer):
    personaSolicitud_id = serializers.IntegerField()
    nombre = serializers.CharField()
    fechaSolicitud = serializers.DateTimeField()


class SerializerChangeRequestStatus(serializers.Serializer):
    estado_id = serializers.IntegerField()

    def update(self, instance):
        instance.estado_id = self.validated_data.get('estado_id')
        instance.save()


class SerializerListAPICredentials(serializers.Serializer):
    personaRel_id = serializers.IntegerField()
    username = serializers.CharField()
    password = serializers.CharField()
    fechaCreacion = serializers.DateTimeField()


class SerializerFilterAPICredentials(serializers.Serializer):
    cuenta_eje_name = serializers.CharField()
    id_cuenta_eje = serializers.IntegerField()
    username = serializers.CharField()
    password = serializers.CharField()
    fechaCreacion = serializers.DateTimeField()


class SerializerUpdateCredentials(serializers.Serializer):
    id_cuenta_eje = serializers.IntegerField()

    def update(self, instance, username, password):
        instance.username = username
        instance.password = password
        instance.save()


class SerializerListCuentaEjeCards(serializers.Serializer):
    ClaveEmpleado = serializers.CharField()
    NumeroCuenta = serializers.CharField()
    tarjeta = serializers.CharField()
    fecha_register = serializers.DateTimeField()


class SerializerCardStock(serializers.Serializer):
    total_tarjetas = serializers.IntegerField()
    total_tarjetas_asignadas = serializers.IntegerField()
    total_tarjetas_disponibles = serializers.IntegerField()


class SerializerPersonalExternoDetail(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()
    curp = serializers.CharField()


"""
    Serializadores usados para recuperar historial de movimientos por cuenta y por tarjeta
"""


class serializerUSertransactionesOut_TmpP1(serializers.Serializer):
    accounts = serializers.SerializerMethodField()

    def get_accounts(self, obj: accounts):
        # Recupera infromacion de la cuenta (relacion persona con cuenta)
        query_set = cuenta.objects.filter(persona_cuenta_id=obj.id)
        serializer = None
        if not query_set:
            message_no_account = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": obj.id,
                        "field": "id_person",
                        "message": "Person with no account",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context["cuenta_eje_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_no_account)
            raise serializers.ValidationError(message_no_account)
        else:
            if self.context["type"] == "card":
                serializer = serializerAccountOutTypeCard_TmpP1(query_set, context=self.context, many=True).data
            elif self.context["type"] == "account":
                serializer = serializerAccountOutTypeAccount_TmpP1(query_set, context=self.context, many=True).data

            return serializer


class serializerAccountOutTypeCard_TmpP1(serializers.Serializer):
    tarjetas = serializers.SerializerMethodField()

    def get_tarjetas(self, obj: tarjetas):
        kward = self.context
        query_set = tarjeta.objects.filter(cuenta_id=obj.id, tarjeta=kward["tarjeta"])
        if not query_set:
            message_no_matching = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": kward["tarjeta"],
                        "field": "tarjeta",
                        "message": "Not matching card with account",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context["cuenta_eje_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_no_matching)
            raise serializers.ValidationError(message_no_matching)
        else:
            return serializerTarjeta_TmpP1(query_set, many=True, context=self.context).data


class serializerAccountOutTypeAccount_TmpP1(serializers.Serializer):
    id = serializers.ReadOnlyField()
    cuenta = serializers.CharField()
    fecha_creacion = serializers.DateTimeField()
    monto = serializers.FloatField()
    cuentaclave = serializers.CharField()
    # is_active = serializers.BooleanField()
    egresos = serializers.SerializerMethodField()
    ingresos = serializers.SerializerMethodField()

    def get_egresos(self, obj: egresos):
        kward = self.context
        kward.pop("tarjeta")
        kward.pop("type")
        kward['cuentatransferencia_id'] = obj.id

        query_set = transferencia.objects.filter(cuenta_emisor=obj.cuenta,
                                                 cuentatransferencia_id=kward['cuentatransferencia_id'],
                                                 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
                                                 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
            '-fecha_creacion')
        if len(query_set) < 5:
            return serializerTransferOut_TmpP1(query_set, many=True, context={'type': 'e'}).data
        else:
            return serializerTransferOut_TmpP1(query_set[0:5], many=True, context={'type': 'e'}).data

    def get_ingresos(self, obj: ingresos):
        kward = self.context
        query_set = transferencia.objects.filter(cta_beneficiario=obj.cuenta,
                                                 cuentatransferencia_id=kward['cuentatransferencia_id'],
                                                 fecha_creacion__date__gte=kward["fecha_creacion__gte"],
                                                 fecha_creacion__date__lte=kward["fecha_creacion__lte"]).order_by(
            '-fecha_creacion')
        # (ChrAva 01.09.2021) Se agrega para regresar los ingresos de la cuenta [PENDIENTE]
        # ---------------------------------------------------------------------------
        if len(query_set) < 5:
            return serializerTransferOut_TmpP1(query_set, many=True, context={'type': 'i'}).data
        else:
            return serializerTransferOut_TmpP1(query_set[0:5], many=True, context={'type': 'i'}).data


class serializerTarjeta_TmpP1(serializers.Serializer):
    id = serializers.ReadOnlyField()
    tarjeta = serializers.CharField()
    # is_active = serializers.BooleanField()
    monto = serializers.FloatField()
    # status = serializers.CharField()
    TarjetaId = serializers.IntegerField()
    NumeroCuenta = serializers.CharField()
    # cvc = serializers.CharField()
    # fechaexp = serializers.DateField()
    alias = serializers.CharField()
    egresos = serializers.SerializerMethodField()
    ingresos = serializers.SerializerMethodField()

    # (ChrAva 06.09.2021) Se agrega por optimizacion en el tiempo de consulta (reducir los 6-8seg)
    respList = None
    respStatus = None

    def get_egresos(self, obj: egresos):
        egresos_list = []
        fecha1 = str(self.context['fecha_creacion__gte']).replace('-', '')
        fecha2 = str(self.context['fecha_creacion__lte']).replace('-', '')
        list, status = get_historial(obj.tarjeta, fecha1, fecha2)
        # (ChrAva 06.09.2021) Se agrega por optimizacion en el tiempo de consulta (reducir los 6-8seg)
        self.respList = list
        for movimiento in list:
            if tipo_movimiento(movimiento['Tipo']) == False:
                if len(egresos_list) < 6:
                    egresos_list.append(movimiento)
                else:
                    break
        query = sorted(egresos_list, key=lambda x: x['Fecha'], reverse=True)
        # (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
        if len(query) < 5:
            return query
        else:
            return query[0:5]

    def get_ingresos(self, obj: ingresos):
        ingresos_list = []
        # (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
        list = self.respList
        for movimiento in list:
            if tipo_movimiento(movimiento['Tipo']):
                if len(ingresos_list) < 6:
                    ingresos_list.append(movimiento)
                else:
                    break
        query = sorted(ingresos_list, key=lambda x: x['Fecha'], reverse=True)
        # (ChrAva 13.09.2021) Se agrega por mejora, regresa los primeros 5 registros
        if len(query) < 5:
            return query
        else:
            return query[0:5]


class serializerTransferOut_TmpP1(serializers.Serializer):
    id = serializers.ReadOnlyField()
    cta_beneficiario = serializers.CharField()
    # clave_rastreo = serializers.CharField()
    # nombre_beneficiario = serializers.CharField()
    rfc_curp_beneficiario = serializers.CharField()
    tipo_pago = serializers.SerializerMethodField()
    tipo_cuenta = serializers.CharField()
    monto = serializers.SerializerMethodField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    #institucion_operante = serializers.CharField()
    empresa = serializers.CharField()
    nombre_emisor = serializers.CharField()
    cuenta_emisor = serializers.CharField()
    fecha_creacion = serializers.DateTimeField()
    transmitter_bank = serializers.SerializerMethodField()
    receiving_bank = serializers.SerializerMethodField()

    def get_transmitter_bank(self, obj: transmitter_bank):
        instance = bancos.objects.get(id=obj.transmitter_bank_id)
        return instance.institucion

    def get_receiving_bank(self, obj: receiving_bank):
        instance = bancos.objects.get(id=obj.receiving_bank_id)
        return instance.institucion

    def get_tipo_pago(self, obj: tipo_pago):
        instance = tipo_transferencia.objects.get(id=obj.tipo_pago_id)
        return instance.nombre_tipo

    def get_monto(self, obj: monto):
        if self.context['type'] == 'i':
            return obj.monto
        if self.context['type'] == 'e':
            return obj.monto * -1


class SerializerPersonalExternoIn(serializers.Serializer):
    name = serializers.CharField()
    last_name = serializers.CharField()
    rfc = serializers.CharField(allow_null=True, allow_blank=True)
    email = serializers.CharField()
    motivo = serializers.CharField(allow_null=True, allow_blank=True)
    fecha_nacimiento = serializers.DateField()

    def validate_email(self, data): #----------------PENDIENTE---------------------
        emails = persona.objects.filter(email=data)
        if len(emails) != 0:
            message_email_already_used = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": data,
                        "field": "email",
                        "message": "Email already used",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context["cuenta_eje_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_email_already_used)
            raise serializers.ValidationError(message_email_already_used)
        else:
            return data

    def create_personalExterno(self, file, cuenta_eje_id):
        fecha_nacimiento = self.validated_data.get("fecha_nacimiento")
        nombre = self.validated_data.get("name")
        last_name = self.validated_data.get("last_name")
        motivo = self.validated_data.get("motivo")
        first_last_name, last_last_name = last_name.split(
            "*")  # de acuerdo con esto el apellido se manda : "Mrcelin*Leyva" ???, por tanto si recibe el apellido SIN * el código truena
        if "*" in last_name:
            apellido = last_name.replace("*", "")  # y entonces ahora con esto quedaría así: "MarcelinLeyva"
        if first_last_name != "" or first_last_name != None:
            password = first_last_name.replace(" ",
                                               "")  # aqui validamos por si el primer apellido me lo envían separado por un espacio? "Marce lin*Leyva"??? PARA APELLIDOS COMPUESTOS
        else:
            password = nombre.replace(" ", "")  # aqui valida que se tengan dos nombres, OK
        password = password + "9/P"
        last_name = last_name.replace("*", " ")
        if file != None:  # volvemos a validar la existencia del documento? Ya se hizo validación desde la vista
            username = generar_username(nombre, apellido)
            if fecha_nacimiento == "" or fecha_nacimiento == None:
                fecha_nacimiento = datetime.date.today()
            instance = persona.objects.create(username=username, motivo=motivo, name=nombre, last_name=last_name,
                                              rfc=self.validated_data.get("rfc"),
                                              fecha_nacimiento=fecha_nacimiento,
                                              email=self.validated_data.get("email"), is_active=True, tipo_persona_id=2,
                                              password=make_password(password))
            dict_documento = {
                "tipo": 12,
                "owner": instance.id,
                "comment": "",
                "base64_file": file
            }
            endpoint = "http://127.0.0.1:8000/api_client/v1/APIPersonaExterna/create/"
            persona_externa_grupopersona(cuenta_eje_id, instance, endpoint)
            try:
                context = {
                    "endpoint": endpoint,
                    "cuenta_eje_id": cuenta_eje_id
                }
                serializer_document = SerializerDocuments(data=dict_documento, context=context)
                if serializer_document.is_valid(raise_exception=True):
                    serializer_document.create(data=dict_documento)
            except:
                message_document_error = {
                    "code": [400],
                    "status": "ERROR",
                    "detail": [
                        {
                            "data": "",
                            "field": "documento",
                            "message": "Error uploading the document",
                        }
                    ]
                }
                RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_document_error)
                raise serializers.ValidationError(message_document_error)

            Cuenta = order_cuenta(instance)
            createWelcomeMessageExternalPerson(instance, password, Cuenta.cuenta, nombre)
        return Cuenta, instance


# (ChrGil 2021-12-07) Serializador para la creación de un documento tipo PDF
class SerializerDocuments(serializers.Serializer):
    tipo = serializers.IntegerField()
    owner = serializers.IntegerField()
    comment = serializers.CharField(allow_null=True, allow_blank=True)
    base64_file = serializers.CharField()

    def validate(self, attrs):
        try:
            obj: TDocumento = TDocumento.objects.get(id=attrs['tipo'])
        except Exception as e:
            message_not_found = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": attrs['tipo'],
                        "field": "tipo",
                        "message": "No matching",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context["cuenta_eje_id"], type=1,
                              endpoint=self.context["endpoint"],
                              objJsonResponse=message_not_found)
            raise serializers.ValidationError(message_not_found)
        else:
            if attrs['comment'] is None:
                attrs['comment'] = obj.descripcion
            file_name = create_file(attrs['base64_file'], attrs['owner'])
            attrs['base64_file'] = file_name

        return attrs

    def create(self, **kwargs):
        file = self.validated_data.pop('base64_file')
        instance = documentos.objects.create_document(**self.validated_data)

        with open(file, 'rb') as document:
            instance.documento = File(document)
            instance.save()
        remove(file)


class SerializerAsignarTarjetasPersonaExterna(serializers.Serializer):
    tarjeta = serializers.ListField()

    def validate_tarjeta(self, data):
        error = []
        for i in data:
            datos = tarjeta.objects.filter(tarjeta=i, clientePrincipal_id=self.context['empresa_id'])
            if len(datos) != 0:
                continue
            else:
                error.append(i)
        if error:
            message_error_list= {
                                    "code": ["400"],
                                    "status": ["error"],
                                    "detail": [{"message": "No se pudo asignar la tarjeta"},
                                                {"field": "tarjeta", "message": "Tarjeta no encontrada",
                                                "data": error}]
                                }
            RegisterSystemLog(idPersona=self.context['empresa_id'], type=1,
                              endpoint=self.context['endpoint'],
                              objJsonResponse=message_error_list)
            raise serializers.ValidationError()
        return data

    def update(self, instance, instanceP, cuenta_eje_id, endpoint:str):
        numerotarjeta = self.validated_data.get("tarjeta")
        lista = []
        for numero_tarjeta in numerotarjeta:
            instanceTarjeta = tarjeta.objects.get(tarjeta=numero_tarjeta)
            if instanceTarjeta.status == "04":
                apellidos = separar_apellidos(instanceP)
                if apellidos[0] == "":
                    apellido_paterno = "NA"
                else:
                    apellido_paterno = apellidos[0]
                if apellidos[1] == "":
                    apellido_materno = "NA"
                else:
                    apellido_materno = apellidos[1]
                if instanceTarjeta.ClaveEmpleado == "":
                        #nueva_clave = clave_empleado()  # Produccion
                        nueva_clave = ClaveEmpleadoPrueba() #Prueba
                        instanceTarjeta.ClaveEmpleado = nueva_clave
                        instanceTarjeta.save()

                if instanceP.rfc == "":
                    rfc = "AAAA010101AAA"
                else:
                    rfc = instanceP.rfc


                diccionario = [
                    {
                        "TarjetaId": instanceTarjeta.TarjetaId,
                        "ClienteId": "C000022",  #C000682 ----> Produccion, C000022 -----> Pruebas
                        "ProductoId": 56,  # 56
                        "Nombre": instanceP.name,
                        "ApellidoPaterno": apellido_paterno,
                        "ApellidoMaterno": apellido_materno,
                        "NombreCorto": "",
                        #"RFC": instanceP.rfc, #--------> "RFC": "AAAA010101AAA", lo coloco si el usuario no tiene un rfc para poder dar de alta la tarjeta en inntec
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
                        "CorreoElectronico": instanceP.email,
                        "CodigoPostal": "",
                        "MontoInicial": "0.0",
                        "ClaveEstado": "",
                        "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
                        "CodigoRetenedora": ""
                    }
                ]
                #AsignarTarjetaPersonaExternaInntec(diccionario)
                AsignarTarjetaPersonaExternaInntecPrueba(diccionario) #Pruebas
                instanceTarjeta.status = "00"
                instanceTarjeta.is_active = True
                instanceTarjeta.cuenta_id = instance.id
                instanceTarjeta.statusInterno_id = 2
                instanceTarjeta.save()
                lista.append(numero_tarjeta)
            else:
                # raise ValidationError({"error": {"Tarjeta ya asignada": instanceTarjeta.tarjeta}})}
                message_card_already_asign = {"code": ["400"], "status": ["error"],
                                                   "detail": [{"message": "No se pudo asignar la tarjeta"},
                                                              {"field": "tarjeta", "message": "Tarjeta ya asignada",
                                                               "data": instanceTarjeta.tarjeta}]}
                RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                                  endpoint=endpoint,
                                  objJsonResponse=message_card_already_asign)

                raise serializers.ValidationError(message_card_already_asign)
        return lista


# SERIALIZADOR TEMPORAL: Serializador de apoyo para asignar tarjetas a Cuenta eje

class SerializerAsignarTarjetasCuentaEje(serializers.Serializer):
    # tarjeta = ListField()

    def validar_tarjetas(self, tarjetas):
        error = []
        datos_tarjeta_inntec = []
        token, _ = get_token_test()
        queryset = get_CardsStockMasivoPrueba(token)

        for numero_tarjeta in tarjetas:
            if len(numero_tarjeta) != 16:
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta no encontrada"})
            datos_tarjetas = listCardMasivoPrueba(numero_tarjeta, queryset)
            if datos_tarjetas:
                datos_tarjeta_inntec.append(datos_tarjetas)
            else:
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta registrada"})
        MensajeError(error)
        return tarjetas, datos_tarjeta_inntec, token

    def create(self, instance, tarjetas, datos_tarjeta_inntec, token):
        Clave_Empleado = ClaveEmpleadoMasivoPrueba(token, datos_tarjeta_inntec)  # Prueba

        tarjeta.objects.bulk_create([
            tarjeta(
                tarjeta=datos["tarjeta"], is_active=False,
                rel_proveedor_id=1,
                TarjetaId=datos["TarjetaId"],
                NumeroCuenta=datos["NumeroCuenta"],
                status="04", clientePrincipal_id=instance.id, ClaveEmpleado=datos["ClaveEmpleado"]
            ) for datos in Clave_Empleado
        ]
        )
        return tarjetas


"""
    A continuación serializadores para dispersiones masivas
"""


class SerializerDisMassivas(serializers.Serializer):
    observations = serializers.CharField(max_length=40)
    date_liberation = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        attrs['date_liberation'] = datetime.datetime.now()
        return attrs

    def create(self, validated_data):
        return transmasivaprod.objects.create(**validated_data).id


class SerializerDispersionTest(serializers.Serializer):
    cta_beneficiario = serializers.CharField(max_length=10, min_length=10)
    nombre_beneficiario = serializers.CharField(max_length=40)
    monto = serializers.FloatField()
    email = serializers.CharField(read_only=True)
    concepto_pago = serializers.CharField(read_only=True, max_length=40)
    is_schedule = serializers.BooleanField(read_only=True)
    empresa = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    nombre_emisor = serializers.CharField(read_only=True)
    cuenta_emisor = serializers.CharField(read_only=True)
    cuentatransferencia_id = serializers.IntegerField(read_only=True)
    masivo_trans_id = serializers.IntegerField(read_only=True, default=None)

    def validate(self, attrs):
        list_errors = ErrorsList()
        list_errors.clear_list()

        context = self.context
        cuenta_emisor_dict: Dict = context['cuenta_emisor']
        cta_beneficiario = cuenta.objects.filter(cuenta=attrs['cta_beneficiario'], persona_cuenta__state=True).first()

        if cta_beneficiario:
            if not cta_beneficiario.is_active:
                ErrorsList("cta_beneficiario", f"{attrs['cta_beneficiario']}",
                           message="Innactive receving account, imposible dispersion")

        if not cuenta_emisor_dict['is_active']:
            print("Cuenta EMISOR: " + cuenta_emisor_dict['cuenta'])
            ErrorsList("cuenta_emisor", f"{cuenta_emisor_dict['cuenta']}",
                       message="Innactive transmitter account, imposible dispersion")

        if context['monto_total'] > cuenta_emisor_dict['monto']:
            ErrorsList("cuenta_emisor", "monto_total", message="Not enough funds in this account to make this dispersion")

        if list_errors.len_list_errors() > 0:
            RegisterSystemLog(idPersona=context['cuenta_eje_id'], type=1,
                              endpoint=context['endpoint'],
                              objJsonResponse=list_errors.standard_error_responses())
            raise serializers.ValidationError(list_errors.standard_error_responses())

        list_errors.clear_list()
        attrs['concepto_pago'] = context['observation']
        attrs['empresa'] = context['empresa']
        attrs['nombre_emisor'] = context['nombre_emisor']
        attrs['cuenta_emisor'] = cuenta_emisor_dict['cuenta']
        attrs['cuentatransferencia_id'] = cuenta_emisor_dict['id']
        attrs['masivo_trans_id'] = context['masivo_trans_id']
        attrs['is_schedule'] = context['is_schedule']
        return attrs

    def create_disper(self, validated_data, monto_actual, schedule):
        instance_cuenta_emisor = self.context['instance_cuenta_emisor']
        cta_beneficario = validated_data['cta_beneficiario']
        tmp_cta_beneficario = cta_beneficario
        instance_benef = cuenta.objects.get(cuenta=cta_beneficario)
        instance_persona = persona.objects.get(id=instance_benef.persona_cuenta_id)

        cta_beneficiario = cuenta.objects.select_for_update().get(cuenta=cta_beneficario)
        instance_disper = transferencia.objects.create_disper(
            **validated_data,
            saldo_remanente=monto_actual
        )

        if not validated_data['is_schedule']:
            t = transferencia.objects.select_for_update().get(id=instance_disper.id)
            with atomic():
                instance_cuenta_emisor.monto -= t.monto
                instance_cuenta_emisor.save()

                cta_beneficiario.monto += t.monto
                cta_beneficiario.save()
                #se notifica al beneficiario
                enviarSMS(t.monto, instance_persona)

            # preparingNotification(cuentaBeneficiario=tmp_cta_beneficario, opcion=3) ****PREGUNTAR A AME*****

            return True

        instance_disper.status_trans_id = 3
        instance_disper.save()
        #Se crea el registro de la transaccion masiva programada (Dispersion)
        self.create_schedule_disper(
            self.validated_data.get("masivo_trans_id"),
            schedule
        )

        return True
    def create_schedule_disper(self,masiva_trans_id: int, fechaEjecucion: Dict):
        schedule = fechaEjecucion["fechaProgramada"]
        schedule_datetime = datetime.datetime.strptime(schedule, "%Y-%m-%d %H:%M:%S")
        #print("Hora formateada" + schedule_datetime)
        masiva_trans_id = TransMasivaProg.objects.create(
            fechaProgramada = schedule_datetime,
            fechaEjecucion = schedule_datetime,
            masivaReferida_id = masiva_trans_id
        )
        return True


"""
    Serializadores para dispersiones individuales
"""


class serialzierCreateTransaction(serializers.Serializer):
    cta_beneficiario = serializers.CharField()
    nombre_beneficiario = serializers.CharField()
    monto = serializers.FloatField()
    concepto_pago = serializers.CharField()
    referencia_numerica = serializers.CharField()
    nombre_emisor = serializers.CharField()
    cuenta_emisor = serializers.CharField()
    cuentatransferencia = serializers.IntegerField()
    transmitter_bank = serializers.IntegerField()
    receiving_bank = serializers.IntegerField()

    def validate_transmitter_bank(self, value):
        queryBancoEmisor = bancos.objects.filter(id=value).exists()
        if not queryBancoEmisor:
            message_not_found_transmitter_bank = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": value,
                        "field": "transmitter_bank",
                        "message": "Not Found Transmitter Bank ",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context['cuenta_eje_id'], type=1,
                              endpoint=self.context['endpoint'],
                              objJsonResponse=message_not_found_transmitter_bank)
            raise serializers.ValidationError(message_not_found_transmitter_bank)
        return value

    def validate_receiving_bank(self, value):
        queryBancoReceptor = bancos.objects.filter(id=value).exists()
        if not queryBancoReceptor:
            message_not_found_receiving_bank = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "data": value,
                        "field": "receiving_bank",
                        "message": "Not Found Receiving Bank",
                    }
                ]
            }
            RegisterSystemLog(idPersona=self.context['cuenta_eje_id'], type=1,
                              endpoint=self.context['endpoint'],
                              objJsonResponse=message_not_found_receiving_bank)
            raise serializers.ValidationError(message_not_found_receiving_bank)
        return value

    def save(self, cuenta_beneficiario, cuenta_emisor, clientInstace, cuenta_eje_id, endpoint:str):
        instanceTransaccion = transferencia.objects.create_transfer(tipo_pago = 3,
                                                                    cta_beneficiario = self.validated_data.get('cta_beneficiario'),
                                                                    nombre_beneficiario = self.validated_data.get('nombre_beneficiario'),
                                                                    transmitter_bank = self.validated_data.get('transmitter_bank'),
                                                                    monto = self.validated_data.get('monto'),
                                                                    concepto_pago = self.validated_data.get('concepto_pago'),
                                                                    referencia_numerica = self.validated_data.get('referencia_numerica'),
                                                                    nombre_emisor = self.validated_data.get('nombre_emisor'),
                                                                    cuenta_emisor = self.validated_data.get('cuenta_emisor'),
                                                                    cuentatransferencia = self.validated_data.get('cuentatransferencia'),
                                                                    receiving_bank=self.validated_data.get('receiving_bank'),
                                                                    status_trans = 1)
        cuenta_emisor.monto -= instanceTransaccion.monto
        cuenta_emisor.save()
        queryTipo = tipo_transferencia.objects.get(id=instanceTransaccion.tipo_pago_id)
        # Entre cuenta Polipay a Tarjeta Polipay
        if queryTipo.nombre_tipo == 'Interno':
            response, statusCode = create_disper(cuenta_beneficiario.TarjetaId, instanceTransaccion.monto)

            cuenta_beneficiario.monto += instanceTransaccion.monto
            cuenta_beneficiario.save()

            if str(statusCode) == '400' or str(statusCode) == '401' or str(statusCode) == '500' or str(
                statusCode) != '200':
                cuenta_emisor.monto += instanceTransaccion.monto
                cuenta_emisor.save()
                instanceTransaccion.delete()
                if response['Message'] == "Datos Incorrectos":
                    message_error_inntec = {
                        "code": [400],
                        "status": "ERROR",
                        "detail": [
                            {
                                "data": "",
                                "field": "",
                                "message": "Invalid data, please verify data",
                            }
                        ]
                    }
                    RegisterSystemLog(idPersona=cuenta_eje_id, type=1,
                                      endpoint=endpoint,
                                      objJsonResponse=message_error_inntec)

                    raise serializers.ValidationError(message_error_inntec)
        createMessageTransactionSend(clientInstace, instanceTransaccion, instanceTransaccion)
        enviarSMS(instanceTransaccion.monto, clientInstace)



