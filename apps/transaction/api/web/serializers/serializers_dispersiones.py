import datetime
from typing import List, Dict

from django.db.transaction import atomic
from django.db.models import Q

from rest_framework.serializers import *

from MANAGEMENT.TaskPlanner.Dispersions.programacion_eventos import create_schedule
from polipaynewConfig.exceptions import add_list_errors, ErrorsList
from apps.transaction.management import CrearComprobanteDispersionPDF
from apps.transaction.models import transferencia, transferenciaProg, transmasivaprod
from apps.users.management import get_Object_orList_error
from apps.users.models import persona, cuenta, documentos
from apps.transaction.management import preparingNotification


# from programacion_eventos import create_schedule


class SerializerDispersionTest(Serializer):
    cta_beneficiario = CharField(max_length=10, min_length=10)
    nombre_beneficiario = CharField(max_length=40)
    monto = FloatField()
    email = CharField(read_only=True)
    concepto_pago = CharField(read_only=True, max_length=40)
    is_schedule = BooleanField(read_only=True)
    empresa = CharField(read_only=True, allow_null=True, allow_blank=True)
    nombre_emisor = CharField(read_only=True)
    cuenta_emisor = CharField(read_only=True)
    cuentatransferencia_id = IntegerField(read_only=True)
    masivo_trans_id = IntegerField(read_only=True, default=None)

    def validate(self, attrs):
        list_errors = ErrorsList()
        list_errors.clear_list()

        context = self.context
        cuenta_emisor_dict: Dict = context['cuenta_emisor']
        cta_beneficiario = cuenta.objects.filter(cuenta=attrs['cta_beneficiario'], persona_cuenta__state=True).first()

        if context['logitud_lista'] > 1 and context['type_dispersion'] == 'I':
            ErrorsList("TypeDispersion", "I",
                       message="Estas haciendo una dispersión utilizando TypeDispersion en modo Individual")

        if cta_beneficiario is None:
            ErrorsList("cta_beneficiario", f"{attrs['cta_beneficiario']}",
                       message="Cuenta del beneficiario no existe o fue eliminado.")

        if cta_beneficiario:
            if not cta_beneficiario.is_active:
                ErrorsList("cta_beneficiario", f"{attrs['cta_beneficiario']}",
                           message="La cuenta del beneficiario se encuentra desactivada")

        if not cuenta_emisor_dict['is_active']:
            ErrorsList("cuenta_emisor", f"{attrs['cuenta_emisor']}",
                       message="No puedes hacer una dispersión si tu cuenta esta desactivada")

        if context['monto_total'] > cuenta_emisor_dict['monto']:
            ErrorsList("cuenta_emisor", None, message="No cuentas con el saldo suficiente para hacer esta dispersión.")

        if list_errors.len_list_errors() > 0:
            raise ValidationError(list_errors.standard_error_responses())

        list_errors.clear_list()
        attrs['concepto_pago'] = context['observation']
        attrs['empresa'] = context['empresa']
        attrs['nombre_emisor'] = context['nombre_emisor']
        attrs['cuenta_emisor'] = cuenta_emisor_dict['cuenta']
        attrs['cuentatransferencia_id'] = cuenta_emisor_dict['id']
        attrs['masivo_trans_id'] = context['masivo_trans_id']
        attrs['is_schedule'] = context['is_schedule']
        return attrs

    def create_disper(self, validated_data, monto_actual):
        instance_cuenta_emisor = self.context['instance_cuenta_emisor']
        cta_beneficario = validated_data['cta_beneficiario']
        tmp_cta_beneficario = cta_beneficario

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

            # se notifica al beneficiario
            preparingNotification(cuentaBeneficiario=tmp_cta_beneficario, opcion=3)

            return True

        instance_disper.status_trans_id = 3
        instance_disper.save()
        return True


class SerializerProgramarDisper(Serializer):
    transferReferida_id = IntegerField(default=0)
    fechaProgramada = DateTimeField(allow_null=True)
    fechaEjecucion = DateTimeField(default=None)


class SerializerDispersion(Serializer):
    cta_beneficiario = CharField()
    nombre_beneficiario = CharField()
    monto = FloatField()
    concepto_pago = CharField()
    is_schedule = BooleanField(read_only=True)
    empresa = CharField(read_only=True, allow_null=True, allow_blank=True)
    nombre_emisor = CharField(read_only=True)
    cuenta_emisor = CharField(read_only=True)
    cuentatransferencia_id = IntegerField(read_only=True)
    masivo_trans_id = IntegerField(read_only=True, default=None)
    schedule = SerializerProgramarDisper()

    def validate(self, attrs):
        list_errors: List = []
        attrs['is_schedule'] = False
        get_cuenta: Dict = self.context['instance_cuenta_emisor'].get_all_cuentas()
        cta_beneficiario = cuenta.objects.filter(cuenta=attrs["cta_beneficiario"]).first()

        if attrs['is_schedule']:
            if attrs['schedule']['fechaProgramada'] is None:
                add_list_errors({'schedule': 'Debes de definir la fecha a dispersar.'}, list_errors)

        if cta_beneficiario is None:
            raise ValidationError({'status': ['La cuenta beneficiario no existe.']})

        if not cta_beneficiario.is_active:
            add_list_errors({'cta_beneficiario': 'Cuenta de beneficiario inactiva'}, list_errors)

        if not get_cuenta['is_active']:
            add_list_errors({'cuenta_emisor': 'Cuenta inactiva'}, list_errors)

        if get_cuenta['monto'] < attrs['monto']:
            add_list_errors({'monto': 'Saldo insuficiente'}, list_errors)

        if len(list_errors) > 0:
            raise ValidationError(
                {'status': list_errors})

        attrs['empresa'] = self.context['empresa']
        attrs['nombre_emisor'] = self.context['nombre_emisor']
        attrs['cuenta_emisor'] = get_cuenta['cuenta']
        attrs['cuentatransferencia_id'] = get_cuenta['id']
        attrs['masivo_trans_id'] = None

        return attrs

    def create(self, **kwargs):
        instance_cuenta_emisor = self.context['instance_cuenta_emisor']
        cta_beneficario = self.context['cta_beneficario']
        schedule = self.validated_data.pop('schedule')

        cta_beneficiario = cuenta.objects.filter(cuenta=cta_beneficario).first()
        instance_disper = transferencia.objects.create_disper(**self.validated_data)

        if not self.validated_data['is_schedule']:
            instance_cuenta_emisor.monto -= instance_disper.monto
            instance_cuenta_emisor.save()

            cta_beneficiario.monto += instance_disper.monto
            cta_beneficiario.save()
            return True

        instance_disper.status_trans_id = 3
        instance_disper.save()

        self.create_schedule_disper(
            instance_disper.id,
            instance_cuenta_emisor.id,
            cta_beneficiario.id,
            schedule
        )

        return True

    def create_schedule_disper(self, id_dispersion: int, id_emisor: int, id_beneficiario: int, validated_data: Dict):
        schedule = validated_data

        if schedule['fechaProgramada']:
            transferenciaProg.objects.create(
                transferReferida_id=id_dispersion,
                fechaProgramada=schedule['fechaProgramada'],
                fechaEjecucion=datetime.datetime.now()
            )

            DATE_SCHEDULE = str(schedule['fechaProgramada'])
            COMMENT = f'{id_dispersion}_{id_emisor}_{id_beneficiario}'

            if not create_schedule(DATE_SCHEDULE, COMMENT):
                t = transferencia.objects.filter(id=id_dispersion)
                t.update(status_trans_id=2)

        return True


class serializerDetailDispercionIndividual(Serializer):
    id = ReadOnlyField()
    nombre_beneficiario = ReadOnlyField()
    monto = CharField()
    concepto_pago = CharField()
    fecha_creacion = CharField()
    email = SerializerMethodField()
    cta_beneficiario = CharField()
    cuenta_emisor = CharField()

    def get_email(self, obj: email):
        get_cta_beneficiario = self.context["instance_cta_benef"]

        for i in get_cta_beneficiario:
            email = get_Object_orList_error(cuenta, cuenta=i.cta_beneficiario).get_email()
            return email


class SerializerListDispersiones(Serializer):
    """
    Filtrador de dispersiones individuales


    """
    tipo_pago_id = IntegerField()
    status_trans_id = IntegerField()
    nombre_beneficiario = CharField(allow_blank=True)
    nombre_emisor = CharField(allow_blank=True)
    cuentatransferencia_id = IntegerField()
    date_1 = DateTimeField()
    date_2 = DateTimeField()

    def queryset(self, validated_data):
        name = validated_data.pop('nombre_beneficiario')
        date_1 = validated_data.pop('date_1')
        date_2 = validated_data.pop('date_2')
        emisor = validated_data.pop('nombre_emisor')

        queryset = transferencia.objects.all().values(
            'id',
            'nombre_beneficiario',
            'monto',
            'fecha_creacion',
            'nombre_emisor',
            'masivo_trans'
        ).filter(
            nombre_beneficiario__icontains=name,
            nombre_emisor__icontains=emisor,
            date_modify__range=(date_1, date_2),
            masivo_trans__isnull=True,
        ).filter(**validated_data).order_by('-fecha_creacion')

        return queryset


class SearializerMassive(SerializerDispersion):
    schedule = CharField(read_only=True)

    def create(self, **kwargs):
        instance_cuenta_emisor = self.context['instance_cuenta_emisor']
        instance_cta_benef = self.context['instance_cta_benef']
        id_massive_trans = self.context['id_massive']

        self.validated_data['masivo_trans_id'] = id_massive_trans
        instance_disper = transferencia.objects.create_disper(**self.validated_data)

        instance_cuenta_emisor.monto -= instance_disper.monto
        instance_cuenta_emisor.save()

        instance_cta_benef.monto += instance_disper.monto
        instance_cta_benef.save()

        return True


class SerializerDisMassivas(Serializer):
    observations = CharField(max_length=40)
    date_liberation = DateTimeField(read_only=True)

    def validate(self, attrs):
        attrs['date_liberation'] = datetime.datetime.now()
        return attrs

    def create(self, validated_data):
        return transmasivaprod.objects.create(**validated_data).id


class ShowDetailSerializer(Serializer):
    details = SerializerMethodField()

    def get_details(self, obj: details) -> Dict:
        data_dispersion = obj.show_datil_dispersion()
        email_cta_beneficiario = cuenta.objects.get(cuenta=data_dispersion['cta_beneficiario']).get_email()
        data_dispersion['email'] = email_cta_beneficiario

        return data_dispersion


class SerializerDocInd(Serializer):
    documento = FileField()

    def validate(self, attrs):
        return attrs


class SerializerDocIndIn(Serializer):
    id = IntegerField()

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        instance_disper = transferencia.objects.get(id=validated_data.get("id"))
        beneficiario = instance_disper.nombre_beneficiario
        userId = self.context["admin_id"]
        documentoId = CrearComprobanteDispersionPDF(instance_disper, beneficiario, userId)
        instance = documentos.objects.get(id=documentoId)
        return SerializerDocInd(instance)
