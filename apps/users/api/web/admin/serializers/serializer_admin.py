import random
import string

from django.db.models import Q
from rest_framework.serializers import *
from rest_framework import serializers

from MANAGEMENT.Utils.utils import random_password
from apps.transaction.models import transferencia, catMaStatus, transmasivaprod
from apps.users.models import persona, cuenta, grupoPersona
from apps.users.management import generate_password, filter_object_if_exist, concentrateFile
from polipaynewConfig import settings
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info


class CreateAdminSerializerIn(Serializer):
    email = EmailField()
    name = CharField()
    a_paterno = CharField()
    a_materno = CharField(allow_null=True, default=None)
    password = CharField(read_only=True)
    phone = IntegerField()
    is_superuser = BooleanField()
    is_staff = BooleanField()
    fecha_nacimiento = DateField()

    def validate(self, attrs):
        email_if_exists = filter_object_if_exist(persona, email=attrs['email'])
        is_superuser = filter_object_if_exist(persona, username=self.context['super_admin'], is_superuser=True)

        if not is_superuser:
            error = {'status': ['Esta operación solo la puede realizar el superusuario']}
            self.context.get('log').json_response(error)
            raise ValidationError(error)

        if self.context['method'] == 'POST':
            if email_if_exists:
                error = {'status': ['Correo electronico ya registrado.']}
                self.context.get('log').json_response(error)
                raise ValidationError(error)

        if self.context['method'] == 'PUT':

            """ Si es diferente entonces valida que no exista ese email """

            if attrs['email'] != self.context['instance'].email:
                if email_if_exists:
                    error = {'status': ['Correo electronico ya registrado.']}
                    self.context.get('log').json_response(error)
                    raise ValidationError(error)

        if attrs['is_superuser']:
            attrs['is_staff'] = True

        attrs['password'] = random_password()
        return attrs

    def create(self, *args):
        return persona.objects.create_admin(**self.validated_data, ip_address=self.context['ip'])

    def update(self, instance, **kwargs):
        instance.email = self.validated_data.get('email', instance.email)
        instance.name = self.validated_data.get('name', instance.name)
        instance.last_name = self.validated_data.get('last_name', instance.last_name)
        instance.phone = self.validated_data.get('phone', instance.phone)
        instance.is_superuser = self.validated_data.get('is_superuser', instance.is_superuser)
        instance.is_staff = self.validated_data.get('is_staff', instance.is_staff)
        instance.fecha_nacimiento = self.validated_data.get('fecha_nacimiento', instance.fecha_nacimiento)
        instance.save()
        return instance


class CreateAdminSerializerOut(Serializer):
    def to_representation(self, instance):
        return {
            "id": instance.id,
            "email": instance.email,
            "name": instance.get_full_name(),
            "phone": instance.phone,
            "is_superuser": instance.is_superuser,
            "is_staff": instance.is_staff,
            "state": instance.state,
            "motivo": instance.motivo
        }


class DeleteAdminSerializerIn(CreateAdminSerializerIn):
    motivo = CharField()

    def validate(self, attrs):
        is_superuser = filter_object_if_exist(persona, username=self.context['super_admin'])

        if not is_superuser:
            error = {'status': ['Esta operación solo la puede realizar el superusuario']}
            self.context.get('log').json_response(error)
            raise ValidationError()

        return attrs

    def update(self, instance, **kwargs):
        instance.motivo = self.validated_data.get('motivo', instance.motivo)
        instance.state = False
        instance.is_activate = False
        instance.save()

        return instance


class ConcentradosIN(Serializer):
    persona = IntegerField()
    tPersona = IntegerField()  # fisica o moral
    ingresos = BooleanField()
    egresos = BooleanField()
    tipoMovimiento = BooleanField()  # 0transferencia o 1dispersion
    fechainicio = DateTimeField()
    fechafin = DateTimeField()
    archivo = BooleanField()

    def validate_persona(self, value):
        pk  = self.initial_data.get("persona")
        queryExistePersona = persona.objects.filter(id=pk).exists()
        if not queryExistePersona:
            raise serializers.ValidationError(value)
        return value

    def getQuery(self, data):
        ingresos = 0
        egresos = 0
        tTransferencia = []
        listPersonas = persona.objects.values('id').filter(tipo_persona_id=data['tPersona'], state=True)
        queryCuentas = cuenta.objects.values('id', 'cuenta', 'cuentaclave').filter(persona_cuenta_id__in=listPersonas)
        cuentas = []
        queryConcentrate = []
        file = ""

        for account in queryCuentas:
            cuentas.append(account['id'])

        if data['tPersona'] == 1 and data['tipoMovimiento'] == 0:  # persona moral y transferencia
            file = "Moral_transferencias"
            if data['egresos'] == 1 and data['ingresos'] == 0:  # unicamente egresos
                tTransferencia.extend([1, 2, 7])
            if data['egresos'] == 0 and data['ingresos'] == 1:  # unicamente ingresos
                tTransferencia.extend([1, 5, 7])
            if data['egresos'] == 1 and data['ingresos'] == 1:  # ambos
                tTransferencia.extend([1, 2, 5, 7])
        elif data['tPersona'] == 1 and data['tipoMovimiento'] == 1:  # persona moral y dispersion
            file = "Moral_dispersiones"
            if data['egresos'] == 1 and data['ingresos'] == 0:  # unicamente egresos
                tTransferencia.append(4)
            if data['egresos'] == 0 and data['ingresos'] == 1:  # unicamente ingresos
                tTransferencia.extend([4, 6])
            if data['egresos'] == 1 and data['ingresos'] == 1:  # ambos
                tTransferencia.extend([4, 6])
        elif data['tPersona'] == 2 and data['tipoMovimiento'] == 0:  # persona fisica y transferencia
            file = "Fisica_transferencias"
            if data['egresos'] == 1 and data['ingresos'] == 0:  # unicamente egresos
                tTransferencia.append(1)
            if data['egresos'] == 0 and data['ingresos'] == 1:  # unicamente ingresos
                tTransferencia.append(1)
            if data['egresos'] == 1 and data['ingresos'] == 1:  # ambos
                tTransferencia.append(1)
        elif data['tPersona'] == 2 and data['tipoMovimiento'] == 1:  # persona fisica y dispersion
            file = "Fisica_dispersiones"
            if data['egresos'] == 1 and data['ingresos'] == 0:  # unicamente egresos
                tTransferencia.append(3)
            if data['egresos'] == 0 and data['ingresos'] == 1:  # unicamente ingresos
                tTransferencia.append(4)
            if data['egresos'] == 1 and data['ingresos'] == 1:  # ambos
                tTransferencia.extend([3, 4])

        if data['egresos'] == 1 and data['ingresos'] == 0:  # clasificamos egresos para consulta
            for account in queryCuentas:
                queryset = transferencia.objects.values('id', 'cta_beneficiario', 'cuenta_emisor',
                                                        'clave_rastreo',
                                                        'fecha_creacion', 'monto', 'referencia_numerica',
                                                        'concepto_pago', 'tipo_pago_id').filter(
                    Q(cuenta_emisor=account['cuenta']) | Q(cuenta_emisor=account['cuentaclave']),
                    cuentatransferencia_id=account['id'],
                    tipo_pago_id__in=tTransferencia,
                    fecha_creacion__range=(data['fechainicio'], data['fechafin'])
                ).order_by("-fecha_creacion")
                for query in queryset:
                    if query['cuenta_emisor'] == account['cuenta'] or query['cuenta_emisor'] == account['cuentaclave']:
                        query['monto'] = round(float(query['monto']), 2) * -1
                        query['monto'] = round(float(query['monto']), 2)
                        egresos += round(float(query['monto']), 2)
                        egresos = round(float(egresos), 2)
                    query['cuentaRel'] = account['cuenta']
                    query['cuentaClaveRel'] = account['cuentaclave']
                    queryConcentrate.append(query)

        elif data['egresos'] == 0 and data['ingresos'] == 1:  # clasificamos ingresos para consulta
            for account in queryCuentas:
                # (ChrAvaBus - mar2022.05.24 11:50)
                queryset = transferencia.objects.values('id', 'cta_beneficiario', 'cuenta_emisor',
                                                        'clave_rastreo',
                                                        'fecha_creacion', 'monto', 'referencia_numerica',
                                                        'concepto_pago', 'tipo_pago_id').filter(
                    Q(cta_beneficiario=account['cuenta']) | Q(cta_beneficiario=account['cuentaclave']),
                    tipo_pago_id__in=tTransferencia,
                    fecha_creacion__range=(data['fechainicio'], data['fechafin'])
                ).order_by("-fecha_creacion")

                for query in queryset:
                    query['cuentaRel'] = account['cuenta']
                    query['cuentaClaveRel'] = account['cuentaclave']

                    if query['cuentaRel'] == query['cta_beneficiario'] or query['cuentaClaveRel'] == query[
                        'cta_beneficiario']:
                        if query['monto'] < 0:
                            query['monto'] = round(float(query['monto']), 2) * -1
                            query['monto'] = round(float(query['monto']), 2)
                        ingresos += round(float(query['monto']), 2)
                        ingresos    = round(float(ingresos), 2)
                        queryConcentrate.append(query)

        elif data['egresos'] == 1 and data['ingresos'] == 1:  # clasificamos ingresos/egresos para consulta
            for account in queryCuentas:
                # (ChrAvaBus - mar2022.05.24 11:50)
                # -------------- EGRESOS -------------
                queryset = transferencia.objects.values('id', 'cta_beneficiario', 'cuenta_emisor',
                                                        'clave_rastreo',
                                                        'fecha_creacion', 'monto', 'referencia_numerica',
                                                        'concepto_pago', 'tipo_pago_id').filter(
                    Q(cuenta_emisor=account['cuenta']) | Q(cuenta_emisor=account['cuentaclave']),
                    cuentatransferencia_id=account['id'],
                    tipo_pago_id__in=tTransferencia,
                    fecha_creacion__range=(data['fechainicio'], data['fechafin'])
                ).order_by("-fecha_creacion")
                for query in queryset:
                    if query['cuenta_emisor'] == account['cuenta'] or query['cuenta_emisor'] == account['cuentaclave']:
                        query['monto'] = round(float(query['monto']),2) * -1
                        query['monto'] = round(float(query['monto']), 2)
                        egresos += round(float(query['monto']), 2)
                        egresos = round(float(egresos), 2)
                        queryConcentrate.append(query)


                # ------------- INGRESOS -------------
                queryset = transferencia.objects.values('id', 'cta_beneficiario', 'cuenta_emisor',
                                                        'clave_rastreo',
                                                        'fecha_creacion', 'monto', 'referencia_numerica',
                                                        'concepto_pago', 'tipo_pago_id').filter(
                    Q(cta_beneficiario=account['cuenta']) | Q(cta_beneficiario=account['cuentaclave']),
                    tipo_pago_id__in=tTransferencia,
                    fecha_creacion__range=(data['fechainicio'], data['fechafin'])
                ).order_by("-fecha_creacion")
                for query in queryset:
                    query['cuentaRel'] = account['cuenta']
                    query['cuentaClaveRel'] = account['cuentaclave']
                    if query['cuentaRel'] == query['cta_beneficiario'] or query['cuentaClaveRel'] == query[
                        'cta_beneficiario']:
                        if query['monto'] < 0:
                            query['monto'] = round(float(query['monto']), 2) * -1
                            query['monto'] = round(float(query['monto']), 2)
                        ingresos += round(float(query['monto']), 2)
                        ingresos    = round(float(ingresos), 2)
                        queryConcentrate.append(query)

        settings.TINGRESOSC = round(float(ingresos), 2)
        settings.TEGRESOSC = round(float(egresos), 2)
        if data["archivo"] == True:
            report = concentrateFile(file, queryConcentrate, data["fechainicio"], data["fechafin"])
            return report

        # (ChrAvaBus - mar2022.05.24 11:50) ordena los movimientos de forma descendente conforme la fecha de creación.
        queryConcentrate.sort(key=lambda x: x["fecha_creacion"], reverse=True)

        return queryConcentrate


class ConcentradosOUT(Serializer):
    id = IntegerField()
    cta_beneficiario = SerializerMethodField()
    cuenta_emisor = SerializerMethodField()
    clave_rastreo = CharField()
    fecha_creacion = DateTimeField()
    monto = FloatField()
    referencia_numerica = CharField()
    concepto_pago = CharField()
    clabe_emisor = SerializerMethodField()
    clabe_receptor = SerializerMethodField()
    tipo_pago_id = IntegerField()

    def get_clabe_emisor(self, obj: clabe_emisor):
        # print(obj)
        return obj['cuenta_emisor']

    def get_clabe_receptor(self, obj: clabe_receptor):
        return obj['cta_beneficiario']

    def get_cuenta_emisor(self, obj: cuenta_emisor):
        # print(obj)
        # print(obj['cuenta_emisor'])
        lnCtEmisor = len(obj['cuenta_emisor'])
        # if lnCtEmisor>8 and obj['tipo_pago_id'] == 3:
        #     return obj['cuenta_emisor']
        if lnCtEmisor > 10:
            return obj['cuenta_emisor'][7:17]
        return obj['cuenta_emisor']

    def get_cta_beneficiario(self, obj: cta_beneficiario):
        lnCtEmisor = len(obj['cta_beneficiario'])
        if lnCtEmisor > 10 and obj['tipo_pago_id'] == 3:
            return obj['cta_beneficiario']
        if lnCtEmisor > 10:
            return obj['cta_beneficiario'][7:17]
        return obj['cta_beneficiario']



class SerializerDashboardAdmin(serializers.Serializer):
    #persona = serializers.IntegerField()
    centro_costo    = serializers.IntegerField()

    """
    def validate_persona(self, value):
        queryExistePersona  = persona.objects.filter(id=value).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(self.initial_data.get("persona"), "BackEnd003")
            r = {"status": msg}
            RegisterSystemLog(idPersona=-value, type=1, endpoint=get_info(self.context), objJsonResponse=r)
            raise serializers.ValidationError(r)

        # Confirmo la relacion de la persona como administrativo de la cuenta eje
        queryExisteAdministrativo = grupoPersona.objects.filter(person_id=value, relacion_grupo_id=3).exists()
        if not queryExisteAdministrativo:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "persona",
                        "data": value,
                        "message": "La persona no tiene relación con una cuenta eje como administrativo."
                    }
                ]
            }
            raise serializers.ValidationError(r)

        return value
    """

    def validate_centro_costo(self, value):
        # Confirmo que exista el id de persoan moral como Cuenta eje o centro de costos
        queryExisteCentroCosto  = persona.objects.filter(id=value, tipo_persona_id=1).exists()
        if not queryExisteCentroCosto:

            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "centro_costo",
                        "data": value,
                        "message": "El cento de costos no existe en el sistema."
                    }
                ]
            }
            self.context.get('log').json_response(r)
            raise serializers.ValidationError(r)

        return value


    def validate(self, data):
        tmp_message = "centro de costos"
        # Confirmo que el centro de costos sea un cento de costo (Polipay Empresa y Liberate requiere cento de costos)
        queryEsCentroCosto  = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).exists()
        if not queryEsCentroCosto:

            queryEsCuentaEje = grupoPersona.objects.filter(empresa_id=data["centro_costo"],
                                                           relacion_grupo_id=1).exists()
            if not queryEsCuentaEje:
                # Confirmo que sea cuenta eje al no ser centro de costo (Producto Dispera se requiere cuenta eje)
                r = {
                    "code": [400],
                    "status": "ERROR",
                    "detail": [
                        {
                            "field": "centro_costo",
                            "data": data["centro_costo"],
                            "message": "No está registrado como una cuenta eje ni centro de costos."
                        }
                    ]
                }
                self.context.get('log').json_response(r)
                raise serializers.ValidationError(r)

        return data

    def getTransactionSummary(self, data):
        objJson                 = {"empresas":[]}
        arrayTmp_movimientos    = []

        banderaIdentidadCentroCosto = True  # True: es un centro de costos, False: es una cuenta eje
        # Determino si es centro de costos o cuenta eje
        queryEsCentroCosto = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).exists()
        if not queryEsCentroCosto:
            banderaIdentidadCentroCosto = False

        # Recupero el id e la cuenta eje a la que pertenece el administrativo, siempre y cuando sea un centro de costos
        if banderaIdentidadCentroCosto:
            #queryIdCuentaEje    = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=3).values("id", "empresa_id")
            queryIdCuentaEje = grupoPersona.objects.filter(person_id=data["centro_costo"], relacion_grupo_id=5).values("id", "empresa_id")
            idCuentaEje         = queryIdCuentaEje[0]["empresa_id"] # Centro de costo
        else:
            idCuentaEje = data["centro_costo"] # Cuenta eje

        # Recupero todos los centros de costos (sub-empresas) que pertenecen a la cuenta eje
        """
        queryCentroDeCostos = grupoPersona.objects.filter(empresa_id=idCuentaEje, relacion_grupo_id=5).values("id", "person_id",
            "person_id__email", "person_id__name", "person_id__last_name")
        """
        queryCentroDeCostos = persona.objects.filter(id=data["centro_costo"]).values("id", "email", "name", "last_name")
        """
        for centroDeCosto in queryCentroDeCostos:
            centroDeCosto["relacion_id"]        = centroDeCosto.pop("id")
            centroDeCosto["empresa_id"]         = centroDeCosto.pop("person_id")
            centroDeCosto["empresa_email"]      = centroDeCosto.pop("person_id__email")
            centroDeCosto["empresa_name"]       = centroDeCosto.pop("person_id__name")
            centroDeCosto["empresa_lastname"]   = centroDeCosto.pop("person_id__last_name")
        """
        for centroDeCosto in queryCentroDeCostos:
            centroDeCosto["empresa_id"]         = centroDeCosto.pop("id")
            centroDeCosto["empresa_email"]      = centroDeCosto.pop("email")
            centroDeCosto["empresa_name"]       = centroDeCosto.pop("name")
            centroDeCosto["empresa_lastname"]   = centroDeCosto.pop("last_name")

        # Recupero la cuenta y CLABE de cada centro de costos.
        for centroDeCosto in queryCentroDeCostos:
            queryCuenta = cuenta.objects.filter(persona_cuenta_id=centroDeCosto["empresa_id"]).values("id", "cuenta", "cuentaclave", "monto")

            centroDeCosto["empresa_cuenta_id"]  = queryCuenta[0]["id"]
            centroDeCosto["empresa_cuenta"]     = queryCuenta[0]["cuenta"]
            centroDeCosto["empresa_clabe"]      = queryCuenta[0]["cuentaclave"]
            centroDeCosto["empresa_monto"]      = queryCuenta[0]["monto"]


        # Recupero el administrativo del Centro de costos
        """ BORRAR
        existeRepLegalDeCC  = grupoPersona.objects.filter(empresa_id=idCuentaEje, relacion_grupo_id=4).exist()
        if not existeRepLegalDeCC:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "centro_costo",
                        "data": idCuentaEje,
                        "message": "El cento de costos no tiene asignado un Representante Legal."
                    }
                ]
            }
            raise serializers.ValidationError(r)
        for centroDeCosto in queryCentroDeCostos:
            queryAdminCC    = grupoPersona.objects.filter(empresa_id=idCuentaEje, relacion_grupo_id=4).values("id", "person_id")
            centroDeCosto["empresa_representante_legal_id"] = queryAdminCC[0]["person_id"]
        """

        # ::: Recorro los centros de costos para recuperar sus movimientos :::
        for centroDeCosto in queryCentroDeCostos:
            queryMovimientos    = transferencia.objects.filter(
                Q(cuenta_emisor=centroDeCosto["empresa_cuenta"]) | Q(cuenta_emisor=centroDeCosto["empresa_clabe"]) |
                Q(cta_beneficiario=centroDeCosto["empresa_cuenta"]) | Q(cta_beneficiario=centroDeCosto["empresa_clabe"]) ).values(
                "id", "monto", "cuenta_emisor", "cta_beneficiario", "tipo_pago_id", "status_trans_id", "masivo_trans_id",
                "masivo_trans__statusRel_id")

            for movimiento  in queryMovimientos:
                #movimiento["masiva_status_trans_id"]    = movimiento.pop("masivo_trans_id__statusRel_id__id")
                movimiento["masiva_status_trans_id"] = movimiento.pop("masivo_trans__statusRel_id")
                arrayTmp_movimientos.append( movimiento )


        if banderaIdentidadCentroCosto:
            # ::: Recorro todos los movimientos de todos los centros de costos:::
            arrayTmp_categorias = {
                "polipay_a_polipay":"",
                "polipay_a_terceros": "",
                "polipay_dispersiones": "",
                "cuentas_propias": ""
            }

            for centroDeCosto in queryCentroDeCostos:

                #print("CC_cuenta["+str(centroDeCosto["empresa_cuenta"])+"]   CC_clabe["+str(centroDeCosto["empresa_clabe"])+"]")

                # ---------------------------------------------------------------------------------------------------------------------------

                #   Caso 1: Polipay a polipay
                #print("         CASO_1: Polipay a Polipay")
                tmp_mon_env = 0.0
                tmp_num_env = 0.0
                tmp_mon_rec = 0.0
                tmp_num_rec = 0.0
                arrayTmp_caso_1 = {
                    "enviadas": {
                        "monto_total": tmp_mon_env,
                        "movimientos": tmp_num_env
                    },
                    "recibidas": {
                        "monto_total": tmp_mon_rec,
                        "movimientos": tmp_num_rec
                    }
                }
                for m in arrayTmp_movimientos:
                    #print("                     movimiento_id["+str(m["id"])+"] monto["+str(m["monto"])+"] cuenta_emisor["+str(m["cuenta_emisor"])+"] cta_beneficiario["+str(m["cta_beneficiario"])+"] tipo_pago["+str(m["tipo_pago_id"])+"] status["+str(m["status_trans_id"])+"] masivo_trans_id["+str(m["masivo_trans_id"])+"] masivo_tipo_id["+str(m["masiva_status_trans_id"])+"]")
                    #       (enviadas)
                    if ( m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"] ) and (
                         m["tipo_pago_id"] == 1 and m["status_trans_id"] == 1 ):
                        tmp_mon_env += round( float(m["monto"]), 2 )
                        tmp_num_env += 1

                    #       (recibidas)
                    if (m["cta_beneficiario"] == centroDeCosto["empresa_cuenta"] or m["cta_beneficiario"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 1 and m["status_trans_id"] == 1):
                        #m["tipo_pago_id"] == 1 or m["tipo_pago_id"] == 5) and (m["status_trans_id"] == 1 or m["status_trans_id"] == 8):
                        tmp_mon_rec += round( float(m["monto"]), 2 )
                        tmp_num_rec += 1

                arrayTmp_caso_1["enviadas"]["monto_total"]  = tmp_mon_env
                arrayTmp_caso_1["enviadas"]["movimientos"]  = tmp_num_env
                arrayTmp_caso_1["recibidas"]["monto_total"] = tmp_mon_rec
                arrayTmp_caso_1["recibidas"]["movimientos"] = tmp_num_rec

                #print("                     enviadas --> monto_total: " + str(tmp_mon_env))
                #print("                     enviadas --> movimientos: " + str(tmp_num_env))
                #print("                     recibidas --> monto_total: " + str(tmp_mon_rec))
                #print("                     recibidas --> movimientos: " + str(tmp_num_rec))

                arrayTmp_categorias["polipay_a_polipay"] = arrayTmp_caso_1

                #---------------------------------------------------------------------------------------------------------------------------

                #   Caso 2: Polipay a terceros
                #print("         CASO_2: Polipay a terceros")
                tmp_mon_ind_cre = 0.0
                tmp_num_ind_cre = 0.0
                tmp_mon_ind_pen = 0.0
                tmp_num_ind_pen = 0.0
                tmp_mon_ind_can = 0.0
                tmp_num_ind_can = 0.0
                tmp_mon_ind_rec = 0.0
                tmp_num_ind_rec = 0.0
                tmp_mon_ind_env = 0.0
                tmp_num_ind_env = 0.0
                tmp_mon_ind_dev = 0.0
                tmp_num_ind_dev = 0.0

                tmp_mon_mas_pen         = 0.0
                tmp_num_mas_pen         = 0.0
                tmp_mon_mas_en_proc     = 0.0
                tmp_num_mas_en_proc     = 0.0
                tmp_mon_mas_can         = 0.0
                tmp_num_mas_can         = 0.0
                tmp_mon_mas_pro         = 0.0
                tmp_num_mas_pro         = 0.0

                arrayTmp_caso_2 = {
                    "individuales": {
                        "creadas":{
                            "monto_total": tmp_mon_ind_cre,
                            "movimientos": tmp_num_ind_cre
                        },
                        "pendientes": {
                            "monto_total": tmp_mon_ind_pen,
                            "movimientos": tmp_num_ind_pen
                        },
                        "canceladas": {
                            "monto_total": tmp_mon_ind_can,
                            "movimientos": tmp_num_ind_can
                        },
                        "enviadas": {
                            "monto_total": tmp_mon_ind_env,
                            "movimientos": tmp_num_ind_env
                        },
                        "recibidas": {
                            "monto_total": tmp_mon_ind_rec,
                            "movimientos": tmp_num_ind_rec
                        },
                        "devoluciones": {
                            "monto_total": tmp_mon_ind_dev,
                            "movimientos": tmp_num_ind_dev
                        }
                    },
                    "masivas": {
                        "pendientes": {
                            "monto_total": tmp_mon_mas_pen,
                            "movimientos": tmp_num_mas_pen
                        },
                        "en_proceso": {
                            "monto_total": tmp_mon_mas_en_proc,
                            "movimientos": tmp_num_mas_en_proc
                        },
                        "canceladas": {
                            "monto_total": tmp_mon_mas_can,
                            "movimientos": tmp_num_mas_can
                        },
                        "procesadas": {
                            "monto_total": tmp_mon_mas_pro,
                            "movimientos": tmp_num_mas_pro
                        }
                    }
                }

                for m in arrayTmp_movimientos:
                    #print("                     movimiento_id["+str(m["id"])+"] monto["+str(m["monto"])+"] cuenta_emisor["+str(m["cuenta_emisor"])+"] cta_beneficiario["+str(m["cta_beneficiario"])+"] tipo_pago["+str(m["tipo_pago_id"])+"] status["+str(m["status_trans_id"])+"] masivo_trans_id["+str(m["masivo_trans_id"])+"] masivo_tipo_id["+str(m["masiva_status_trans_id"])+"]")
                    #       (individuales - creadas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["status_trans_id"] == 6 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_cre += round( float(m["monto"]), 2 )
                        tmp_num_ind_cre += 1

                    #       (individuales - pendiente)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["status_trans_id"] == 3 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_pen += round( float(m["monto"]), 2 )
                        tmp_num_ind_pen += 1

                    #       (individuales - canceladas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["status_trans_id"] == 5 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_can += round( float(m["monto"]), 2 )
                        tmp_num_ind_can += 1

                    #       (individuales - enviadas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["status_trans_id"] == 1 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_env += round( float(m["monto"]), 2 )
                        tmp_num_ind_env += 1

                    #       (individuales - recibidas) Caso particular (Terceros a Polipay, STP, Solicitud de saldos)
                    if (m["cta_beneficiario"] == centroDeCosto["empresa_cuenta"] or m["cta_beneficiario"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 or m["tipo_pago_id"] == 5 or m["tipo_pago_id"] == 6 ) and ( m["masivo_trans_id"] == None ):
                        #m["tipo_pago_id"] == 2 or m["tipo_pago_id"] == 5) and (m["status_trans_id"] == 1 or m["status_trans_id"] == 8) and (
                        #m["masivo_trans_id"] == None):
                        tmp_mon_ind_rec += round( float(m["monto"]), 2 )
                        tmp_num_ind_rec += 1

                    #       (individuales - devueltas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["status_trans_id"] == 7 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_dev += round( float(m["monto"]), 2 )
                        tmp_num_ind_dev += 1


                    #       (masivas - pendientes)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["masiva_status_trans_id"] == 2 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_pen += round( float(m["monto"]), 2 )
                        tmp_num_mas_pen += 1

                    #       (masivas - en_proceso)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                    #if (m["cta_beneficiario"] == centroDeCosto["empresa_cuenta"] or m["cta_beneficiario"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and m["masiva_status_trans_id"] == 4 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_en_proc += round( float(m["monto"]), 2 )
                        tmp_num_mas_en_proc += 1

                    #       (masivas - canceladas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and  m["masiva_status_trans_id"] == 3 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_can += round( float(m["monto"]), 2 )
                        tmp_num_mas_can += 1

                    #       (masivas - procesadas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 2 and  m["masiva_status_trans_id"] == 5 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_pro += round( float(m["monto"]), 2 )
                        tmp_num_mas_pro += 1


                arrayTmp_caso_2["individuales"]["creadas"]["monto_total"]       = tmp_mon_ind_cre
                arrayTmp_caso_2["individuales"]["creadas"]["movimientos"]       = tmp_num_ind_cre
                arrayTmp_caso_2["individuales"]["pendientes"]["monto_total"]    = tmp_mon_ind_pen
                arrayTmp_caso_2["individuales"]["pendientes"]["movimientos"]    = tmp_num_ind_pen
                arrayTmp_caso_2["individuales"]["canceladas"]["monto_total"]    = tmp_mon_ind_can
                arrayTmp_caso_2["individuales"]["canceladas"]["movimientos"]    = tmp_num_ind_can
                arrayTmp_caso_2["individuales"]["enviadas"]["monto_total"]      = tmp_mon_ind_env
                arrayTmp_caso_2["individuales"]["enviadas"]["movimientos"]      = tmp_num_ind_env
                arrayTmp_caso_2["individuales"]["recibidas"]["monto_total"]     = tmp_mon_ind_rec
                arrayTmp_caso_2["individuales"]["recibidas"]["movimientos"]     = tmp_num_ind_rec
                arrayTmp_caso_2["individuales"]["devoluciones"]["monto_total"]  = tmp_mon_ind_dev
                arrayTmp_caso_2["individuales"]["devoluciones"]["movimientos"]  = tmp_num_ind_dev

                arrayTmp_caso_2["masivas"]["pendientes"]["monto_total"] = tmp_mon_mas_pen
                arrayTmp_caso_2["masivas"]["pendientes"]["movimientos"] = tmp_num_mas_pen
                arrayTmp_caso_2["masivas"]["en_proceso"]["monto_total"] = tmp_mon_mas_en_proc
                arrayTmp_caso_2["masivas"]["en_proceso"]["movimientos"] = tmp_num_mas_en_proc
                arrayTmp_caso_2["masivas"]["canceladas"]["monto_total"] = tmp_mon_mas_can
                arrayTmp_caso_2["masivas"]["canceladas"]["movimientos"] = tmp_num_mas_can
                arrayTmp_caso_2["masivas"]["procesadas"]["monto_total"] = tmp_mon_mas_pro
                arrayTmp_caso_2["masivas"]["procesadas"]["movimientos"] = tmp_num_mas_pro

                #print("                     (individuales) creadas --> monto_total: " + str(tmp_mon_ind_cre))
                #print("                     (individuales) creadas --> movimientos: " + str(tmp_num_ind_cre))
                #print("                     (individuales) pendientes --> monto_total: " + str(tmp_mon_ind_pen))
                #print("                     (individuales) pendientes --> movimientos: " + str(tmp_num_ind_pen))
                #print("                     (individuales) canceladas --> monto_total: " + str(tmp_mon_ind_can))
                #print("                     (individuales) canceladas --> movimientos: " + str(tmp_num_ind_can))
                #print("                     (individuales) enviadas --> monto_total: " + str(tmp_mon_ind_env))
                #print("                     (individuales) enviadas --> movimientos: " + str(tmp_num_ind_env))
                #print("                     (individuales) recibidas --> monto_total: " + str(tmp_mon_ind_rec))
                #print("                     (individuales) recibidas --> movimientos: " + str(tmp_num_ind_rec))
                #print("                     (individuales) devoluciones --> monto_total: " + str(tmp_mon_ind_dev))
                #print("                     (individuales) devoluciones --> movimientos: " + str(tmp_num_ind_dev))

                #print("                     (masivas) pendientes --> monto_total: " + str(tmp_mon_mas_pen))
                #print("                     (masivas) pendientes --> movimientos: " + str(tmp_num_mas_pen))
                #print("                     (masivas) en_proceso --> monto_total: " + str(tmp_mon_mas_en_proc))
                #print("                     (masivas) en_proceso --> movimientos: " + str(tmp_num_mas_en_proc))
                #print("                     (masivas) canceladas --> monto_total: " + str(tmp_mon_mas_can))
                #print("                     (masivas) canceladas --> movimientos: " + str(tmp_num_mas_can))
                #print("                     (masivas) procesadas --> monto_total: " + str(tmp_mon_mas_pro))
                #print("                     (masivas) procesadas --> movimientos: " + str(tmp_num_mas_pro))

                arrayTmp_categorias["polipay_a_terceros"] = arrayTmp_caso_2

                # ---------------------------------------------------------------------------------------------------------------------------

                #   Caso 3: Polipay dispersiones
                #print("         CASO_3: Polipay Dispersiones")
                tmp_mon_ind_env = 0.0
                tmp_num_ind_env = 0.0
                tmp_mon_ind_pen = 0.0
                tmp_num_ind_pen = 0.0
                tmp_mon_ind_can = 0.0
                tmp_num_ind_can = 0.0

                tmp_mon_mas_cre = 0.0
                tmp_num_mas_cre = 0.0
                tmp_mon_mas_pen = 0.0
                tmp_num_mas_pen = 0.0
                tmp_mon_mas_can = 0.0
                tmp_num_mas_can = 0.0

                arrayTmp_caso_3 = {
                    "individuales": {
                        "enviadas": {
                            "monto_total": tmp_mon_ind_env,
                            "movimientos": tmp_num_ind_env
                        },
                        "pendientes": {
                            "monto_total": tmp_mon_ind_pen,
                            "movimientos": tmp_num_ind_pen
                        },
                        "canceladas": {
                            "monto_total": tmp_mon_ind_can,
                            "movimientos": tmp_num_ind_can
                        }
                    },
                    "masivas": {
                        "creadas": {
                            "monto_total": tmp_mon_mas_cre,
                            "movimientos": tmp_num_mas_cre
                        },
                        "pendientes": {
                            "monto_total": tmp_mon_mas_pen,
                            "movimientos": tmp_num_mas_pen
                        },
                        "canceladas": {
                            "monto_total": tmp_mon_mas_can,
                            "movimientos": tmp_num_mas_can
                        }
                    }
                }

                for m in arrayTmp_movimientos:
                    #print("                     movimiento_id["+str(m["id"])+"] monto["+str(m["monto"])+"] cuenta_emisor["+str(m["cuenta_emisor"])+"] cta_beneficiario["+str(m["cta_beneficiario"])+"] tipo_pago["+str(m["tipo_pago_id"])+"] status["+str(m["status_trans_id"])+"] masivo_trans_id["+str(m["masivo_trans_id"])+"] masivo_tipo_id["+str(m["masiva_status_trans_id"])+"]")
                    #       (individuales - enviadas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["status_trans_id"] == 1 and m["masivo_trans_id"] == None):
                        #m["tipo_pago_id"] == 1 and m["status_trans_id"] == 1 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_env += round( float(m["monto"]), 2 )
                        tmp_num_ind_env += 1

                    #       (individuales - pendientes)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["status_trans_id"] == 3 and m["masivo_trans_id"] == None):
                        #m["tipo_pago_id"] == 1 and m["status_trans_id"] == 3 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_pen += round( float(m["monto"]), 2 )
                        tmp_num_ind_pen += 1

                    #       (individuales - canceladas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["status_trans_id"] == 5 and m["masivo_trans_id"] == None):
                        #m["tipo_pago_id"] == 1 and m["status_trans_id"] == 5 and m["masivo_trans_id"] == None):
                        tmp_mon_ind_can += round( float(m["monto"]), 2 )
                        tmp_num_ind_can += 1


                    #       (masivas - creadas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["masiva_status_trans_id"] == 1 and m["masivo_trans_id"] != None):
                        #m["tipo_pago_id"] == 1 and  m["masiva_status_trans_id"] == 1 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_cre += round( float(m["monto"]), 2 )
                        tmp_num_mas_cre += 1

                    #       (masivas - pendientes)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["masiva_status_trans_id"] == 2 and m["masivo_trans_id"] != None):
                        #m["tipo_pago_id"] == 1 and m["masiva_status_trans_id"] == 2 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_pen += round( float(m["monto"]), 2 )
                        tmp_num_mas_pen += 1

                    #       (masivas - canceladas)
                    if (m["cuenta_emisor"] == centroDeCosto["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto["empresa_clabe"]) and (
                        m["tipo_pago_id"] == 4 and m["masiva_status_trans_id"] == 3 and m["masivo_trans_id"] != None):
                        #m["tipo_pago_id"] == 1 and m["masiva_status_trans_id"] == 3 and m["masivo_trans_id"] != None):
                        tmp_mon_mas_can += round( float(m["monto"]), 2 )
                        tmp_num_mas_can += 1

                arrayTmp_caso_3["individuales"]["enviadas"]["monto_total"]      = tmp_mon_ind_env
                arrayTmp_caso_3["individuales"]["enviadas"]["movimientos"]      = tmp_num_ind_env
                arrayTmp_caso_3["individuales"]["pendientes"]["monto_total"]    = tmp_mon_ind_pen
                arrayTmp_caso_3["individuales"]["pendientes"]["movimientos"]    = tmp_num_ind_pen
                arrayTmp_caso_3["individuales"]["canceladas"]["monto_total"]    = tmp_mon_ind_can
                arrayTmp_caso_3["individuales"]["canceladas"]["movimientos"]    = tmp_num_ind_can

                arrayTmp_caso_3["masivas"]["creadas"]["monto_total"]    = tmp_mon_mas_cre
                arrayTmp_caso_3["masivas"]["creadas"]["movimientos"]    = tmp_num_mas_cre
                arrayTmp_caso_3["masivas"]["pendientes"]["monto_total"] = tmp_mon_mas_pen
                arrayTmp_caso_3["masivas"]["pendientes"]["movimientos"] = tmp_num_mas_pen
                arrayTmp_caso_3["masivas"]["canceladas"]["monto_total"] = tmp_mon_mas_can
                arrayTmp_caso_3["masivas"]["canceladas"]["movimientos"] = tmp_num_mas_can

                #print("                     (individuales) enviadas --> monto_total: " + str(tmp_mon_ind_env))
                #print("                     (individuales) enviadas --> movimientos: " + str(tmp_num_ind_env))
                #print("                     (individuales) pendientes --> monto_total: " + str(tmp_mon_ind_pen))
                #print("                     (individuales) pendientes --> movimientos: " + str(tmp_num_ind_pen))
                #print("                     (individuales) canceladas --> monto_total: " + str(tmp_mon_ind_can))
                #print("                     (individuales) canceladas --> movimientos: " + str(tmp_num_ind_can))

                #print("                     (masivas) creadas --> monto_total: " + str(tmp_mon_mas_cre))
                #print("                     (masivas) creadas --> movimientos: " + str(tmp_num_mas_cre))
                #print("                     (masivas) pendientes --> monto_total: " + str(tmp_mon_mas_pen))
                #print("                     (masivas) pendientes --> movimientos: " + str(tmp_num_mas_pen))
                #print("                     (masivas) canceladas --> monto_total: " + str(tmp_mon_mas_can))
                #print("                     (masivas) canceladas --> movimientos: " + str(tmp_num_mas_can))

                arrayTmp_categorias["polipay_dispersiones"] = arrayTmp_caso_3

                # ---------------------------------------------------------------------------------------------------------------------------

                #   Caso 4: Cuentas propias
                #print("         CASO_4: Cuentas Propias")
                tmp_monto_emisor    = 0.0
                tmp_numero_emisor   = 0.0
                tmp_monto_receptor  = 0.0
                tmp_numero_receptor = 0.0
                arrayTmp_caso_4 = []

                queryCentroDeCostosHnos = grupoPersona.objects.filter(empresa_id=idCuentaEje, relacion_grupo_id=5).exclude(person_id=data["centro_costo"]).values(
                    "id", "person_id", "person_id__email", "person_id__name", "person_id__last_name")
                for centroDeCosto2 in queryCentroDeCostosHnos:
                    centroDeCosto2["relacion_id"]       = centroDeCosto2.pop("id")
                    centroDeCosto2["empresa_id"]        = centroDeCosto2.pop("person_id")
                    centroDeCosto2["empresa_email"]     = centroDeCosto2.pop("person_id__email")
                    centroDeCosto2["empresa_name"]      = centroDeCosto2.pop("person_id__name")
                    centroDeCosto2["empresa_lastname"]  = centroDeCosto2.pop("person_id__last_name")

                # Recupero la cuenta y CLABE de cada centro de costos.
                for centroDeCosto2 in queryCentroDeCostosHnos:
                    queryCuenta = cuenta.objects.filter(persona_cuenta_id=centroDeCosto2["empresa_id"]).values(
                        "id", "cuenta", "cuentaclave", "monto")
                    centroDeCosto2["empresa_cuenta_id"]  = queryCuenta[0]["id"]
                    centroDeCosto2["empresa_cuenta"]     = queryCuenta[0]["cuenta"]
                    centroDeCosto2["empresa_clabe"]      = queryCuenta[0]["cuentaclave"]
                    centroDeCosto2["empresa_monto"]      = queryCuenta[0]["monto"]

                for centroDeCostoHno in queryCentroDeCostosHnos:

                    # Caso 1: Centro de costos es el emisor
                    for m in arrayTmp_movimientos:

                        if str(m["cuenta_emisor"]) == str(centroDeCosto["empresa_cuenta"]) and str(m["cta_beneficiario"]) == str(centroDeCostoHno["empresa_cuenta"]) and m["tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_emisor    += round( float(m["monto"]), 2 )
                            tmp_numero_emisor   += 1

                        elif str(m["cuenta_emisor"]) == str(centroDeCosto["empresa_clabe"]) and str(m["cta_beneficiario"]) == str(centroDeCostoHno["empresa_clabe"]) and m["tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_emisor    += round( float(m["monto"]), 2 )
                            tmp_numero_emisor   += 1

                        if str(m["cta_beneficiario"]) == str(centroDeCosto["empresa_cuenta"]) and str(m["cuenta_emisor"]) == str(centroDeCostoHno["empresa_cuenta"]) and m["tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_receptor  += round( float(m["monto"]), 2 )
                            tmp_numero_receptor += 1

                        elif str(m["cta_beneficiario"]) == str(centroDeCosto["empresa_clabe"]) and str(m["cuenta_emisor"]) == str(centroDeCostoHno["empresa_clabe"]) and m["tipo_pago_id"] == 7 and m["status_trans_id"] == 1:
                            tmp_monto_receptor  += round( float(m["monto"]), 2 )
                            tmp_numero_receptor += 1


                    if round( float(tmp_monto_emisor), 2 ) > 0.0:
                        arrayTmp_caso_4.append(
                            {
                                "origen": centroDeCosto["empresa_name"],
                                "destino": centroDeCostoHno["empresa_name"],
                                "monto": tmp_monto_emisor,
                                "movimientos": tmp_numero_emisor
                            }
                        )

                    if round( float(tmp_monto_receptor), 2 ) > 0.0:
                        arrayTmp_caso_4.append(
                            {
                                "origen": centroDeCostoHno["empresa_name"],
                                "destino": centroDeCosto["empresa_name"],
                                "monto": tmp_monto_receptor,
                                "movimientos": tmp_numero_receptor
                            }
                        )

                    tmp_monto_emisor    = 0.0
                    tmp_numero_emisor   = 0.0
                    tmp_monto_receptor  = 0.0
                    tmp_numero_receptor = 0.0


                arrayTmp_categorias["cuentas_propias"]  = arrayTmp_caso_4

                # ---------------------------------------------------------------------------------------------------------------------------

                # Se agregan movimientos de cada categoria en cada centro de costos
                centroDeCosto["detalle"]    = arrayTmp_categorias

                arrayTmp_categorias = {
                    "polipay_a_polipay": "",
                    "polipay_a_terceros": "",
                    "polipay_dispersiones": "",
                    "cuentas_propias": ""
                }
        else:
            queryCuentaEje  = persona.objects.filter(id=data["centro_costo"]).values("id", "email", "name", "last_name")
            # ::: Recorro todos los movimientos de la cuenta eje :::
            arrayTmp_categorias = {
                "polipay_a_polipay": [],
                "polipay_a_terceros": [],
                "polipay_dispersiones": [],
                "cuentas_propias": []
            }

            #   Caso 1: Polipay a polipay
            tmp_mon_env = 0.0
            tmp_num_env = 0.0
            tmp_mon_rec = 0.0
            tmp_num_rec = 0.0
            arrayTmp_caso_1 = {
                "enviadas": {
                    "monto_total": tmp_mon_env,
                    "movimientos": tmp_num_env
                },
                "recibidas": {
                    "monto_total": tmp_mon_rec,
                    "movimientos": tmp_num_rec
                }
            }
            for m in arrayTmp_movimientos:
                #       (enviadas)
                if (m["cuenta_emisor"] == centroDeCosto[0]["empresa_cuenta"] or m["cuenta_emisor"] == centroDeCosto[0][
                    "empresa_clabe"]) and (m["tipo_pago_id"] == 4 and m["status_trans_id"] == 1):
                    tmp_mon_env += round( float(m["monto"]), 2 )
                    tmp_num_env += 1

                #       (recibidas)
                if (m["cta_beneficiario"] == centroDeCosto[0]["empresa_cuenta"] or m["cta_beneficiario"] == centroDeCosto[0][
                    "empresa_clabe"]) and (m["status_trans_id"] == 1 or m["status_trans_id"] == 8) and (m["tipo_pago_id"] == 4 or m["tipo_pago_id"] == 5):
                    tmp_mon_rec += round( float(m["monto"]), 2 )
                    tmp_num_rec += 1

            arrayTmp_caso_1["enviadas"]["monto_total"] = tmp_mon_env
            arrayTmp_caso_1["enviadas"]["movimientos"] = tmp_num_env
            arrayTmp_caso_1["recibidas"]["monto_total"] = tmp_mon_rec
            arrayTmp_caso_1["recibidas"]["movimientos"] = tmp_num_rec

            arrayTmp_categorias["polipay_a_terceros"] = arrayTmp_caso_1

            # Se agregan movimientos de cada categoria en cada centro de costos
            centroDeCosto["detalle"] = arrayTmp_categorias


        objJson["empresas"] = queryCentroDeCostos

        return objJson
