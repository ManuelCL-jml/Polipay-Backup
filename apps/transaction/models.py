import string
from typing import Any, Dict
from django.db import models
from .choices import TYPE_ACCOUNT
from .manager import transferenciaManager, FilterTransaction, TransferenciaMasivaManager, ManagerTransMasivaProg, \
    ManagerDetalleTransferencia
from apps.users.models import grupoPersona


class Status(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=30)


class tipo_transferencia(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre_tipo = models.CharField(max_length=20, blank=False, null=False)

    def get_tipo_pago(self):
        return self.nombre_tipo


class catMaStatus(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=10)
    descripcion = models.TextField(max_length=100)


class transmasivaprod(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)  # Se va filtrar
    date_liberation = models.DateTimeField()
    observations = models.CharField(max_length=254)
    file = models.FileField(upload_to='excel_produccion')
    statusRel = models.ForeignKey(catMaStatus, on_delete=models.DO_NOTHING, default=1)
    usuarioRel = models.ForeignKey('users.persona', on_delete=models.DO_NOTHING, null=True, blank=True, default=None)
    objects = TransferenciaMasivaManager()

    class Meta:
        ordering = ['-date_created']

    def get_status(self):
        return self.statusRel_id

    @property
    def get_created_to_transaction_massive(self) -> Dict:
        return {
            "id": self.usuarioRel_id,
            "name": self.usuarioRel.get_full_name(),
            "email": self.usuarioRel.get_email()
        }

    def get_observations(self):
        return self.observations

    def get_only_id(self):
        return self.id

    def get_detail_info(self):
        return {
            "id": self.id,
            "observations": self.observations,
            "date_liberation": self.date_liberation,
            "shedule": self.get_shedule_date()
        }

    def get_shedule_date(self):
        try:
            return TransMasivaProg.objects.get(masivaReferida_id=self.id).get_date_shedule()
        except Exception as e:
            return "No programada"

    @property
    def created_to(self):
        try:
            return self.usuarioRel.get_full_name()
        except AttributeError:
            return None


class bancos(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    clabe = models.CharField(max_length=3, editable=False)
    institucion = models.CharField(max_length=25, blank=False, null=False)
    participante = models.IntegerField(null=False, blank=False)

    def get_institucion(self):
        return self.institucion

    def get_clabe_banco(self):
        return self.clabe

    @property
    def get_banco_id(self) -> int:
        return self.id


class transferencia(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    cta_beneficiario = models.CharField(max_length=20, blank=False, null=False)
    nombre_beneficiario = models.CharField(max_length=40, blank=False, null=False)
    rfc_curp_beneficiario = models.CharField(max_length=18, blank=True, null=True)
    t_ctaBeneficiario = models.IntegerField(choices=TYPE_ACCOUNT, default=1)
    clave_rastreo = models.CharField(max_length=30, blank=False, null=False, editable=False)
    tipo_cuenta = models.CharField(max_length=30, blank=False, null=False)
    monto = models.FloatField(blank=False, null=False)
    concepto_pago = models.CharField(max_length=40, blank=False, null=False)
    referencia_numerica = models.CharField(max_length=50, blank=False, null=False)
    # institucion_operante = models.CharField(max_length=5, blank=False, null=False)
    empresa = models.CharField(max_length=40, blank=False, null=False, default="N/D")

    # (AntAboy 2022-10-11) Catalogo de tipo cuenta Ordenante o emisor
    t_ctaEmisor = models.IntegerField(choices=TYPE_ACCOUNT, default=1)
    nombre_emisor = models.CharField(max_length=45, blank=False, null=False, default="N/D")
    cuenta_emisor = models.CharField(max_length=20, blank=False, null=False)
    rfc_curp_emisor = models.CharField(max_length=18, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    date_modify = models.DateTimeField(blank=True)
    email = models.EmailField(null=True, blank=True)
    programada = models.BooleanField(default=False)
    saldo_remanente = models.FloatField(blank=True, null=True)  # saldo remantente emisor

    # (ChrGil 2022-01-11) API STP
    folio_OpEF = models.CharField(max_length=10, blank=True, null=True) # (AntAboy 2022-10-11) folio operacion Enlace Financiero
    fecha_operacionSTP = models.CharField(max_length=8, null=True) # fecha que proporciona STP si no tiene es operacion manual
    saldo_remanente_beneficiario = models.FloatField(blank=True, null=True, default=0.0) #saldo remanente para el beneficiario

    # (ChrGil 2022-01-11) Llaves Foraneas
    tipo_pago = models.ForeignKey(
        tipo_transferencia,
        on_delete=models.DO_NOTHING,
        null=False,
        blank=False,
        default=1)

    user_autorizada = models.ForeignKey(
        'users.persona',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        default=None)

    masivo_trans = models.ForeignKey(
        transmasivaprod,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="id_masiv")

    status_trans = models.ForeignKey(
        Status,
        on_delete=models.DO_NOTHING,
        blank=False,
        null=False,
        default=1)

    cuentatransferencia = models.ForeignKey(
        'users.cuenta',
        on_delete=models.DO_NOTHING,
        blank=False,
        null=True,
        default=None)

    # (AntAbo 2021-11-24) banco emisor
    transmitter_bank = models.ForeignKey(
        bancos,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="banco_emisor")

    # (AntAbo 2021-11-24) banco receptor / beneficiario
    receiving_bank = models.ForeignKey(
        bancos,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="banco_beneficiario")

    # (AntAbo 2021-11-30) Persona administrador de cta eje / colaborador de centro costos que emite la transaccion
    emisor_empresa = models.ForeignKey(
        'users.persona',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        default=None,
        related_name="emisorEmpresarial")

    objects = transferenciaManager()
    filter_transaction = FilterTransaction()

    class Meta:
        permissions = [('can_create_transfer_v2', 'Puede crear transferencias'),
                       ('can_edit_transfer_v2', 'Puede editar transferencias'),
                       ('can_get_transfer_v2', 'Puede ver transferencias'),
                       ('can_do_all_transfer_v2', 'Puede hacer todo')]

    @property
    def get_only_id_transfer(self):
        return self.id

    @property
    def get_masivo_trans(self) -> int:
        return self.masivo_trans_id

    @property
    def get_monto(self) -> float:
        return self.monto

    @property
    def get_cuenta_emisor(self) -> string:
        return self.cuenta_emisor

    def auth_to(self):
        try:
            return self.user_autorizada.get_full_name()
        except AttributeError as e:
            return None

    def get_dispersion(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "monto": self.monto,
            "status": self.status_trans_id
        }

    def get_massive_dispersion(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "massive": self.masivo_trans.get_transmasivaprod(),
            "emisor": self.nombre_emisor
        }

    def show_datil_dispersion(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre_beneficiario": self.nombre_beneficiario,
            "monto": self.monto,
            "fecha_creacion": self.fecha_creacion,
            "observation": self.masivo_trans.observations,
            "cta_beneficiario": self.cta_beneficiario
        }

    def show_detail_transaction_pending(self) -> Dict[str, Any]:
        return {
            'Cliente': self.empresa,
            'NombreBeneficiario': self.nombre_beneficiario,
            'Email': self.email,
            'Clabe': self.cta_beneficiario,
            'Monto': self.monto,
            'Referencia': self.referencia_numerica,
            'Concepto': self.concepto_pago,
            'FechaDispersion': self.fecha_creacion,
            'Estado': self.status_trans.nombre,
            'EstadoId': self.status_trans_id,
            'Banco': self.get_banco(),
            'ClaveRastreo': self.clave_rastreo,
            'RFC': self.rfc_curp_beneficiario,
        }

    def show_detail_transaction(self) -> Dict[str, Any]:
        data = self.show_detail_transaction_pending()
        data['TipoOperacion'] = self.tipo_pago.nombre_tipo
        data['origen'] = self.masivo_trans_id
        data['NombreOrdenante'] = self.nombre_emisor
        data['CuentaOrigen'] = self.cuenta_emisor
        data['Motivo'] = self.get_motivo()
        return data

    def get_motivo(self):
        try:
            return detalleTransferencia.objects.get(transferReferida_id=self.id).motivo()
        except Exception as e:
            return None

    # Modificado (ChrGil 2021-11-19) Se cambia de banco_beneficiario a banco_beneficiario_id
    def get_banco(self):
        try:
            return bancos.objects.get(id=self.receiving_bank_id).get_institucion()
        except Exception as e:
            return 'Sin banco'

    def show_detail_dispersion(self) -> Dict[str, Any]:
        return {
            'Folio': self.id,
            'Monto': self.monto,
            'Concepto': self.concepto_pago,
            'FechaHora': self.fecha_creacion,
            'CuentaBeneficiario': self.cta_beneficiario,
        }

    # (ChrGil 2021-11-30) Muestra los detalles de transacciones individuales y masivas
    def show_detail_transaction_massive(self) -> Dict[str, Any]:
        return {
            "ClaveRastreo": self.clave_rastreo,
            "NombreBeneficiario": self.nombre_beneficiario,
            "CuentaBeneficiario": self.cta_beneficiario,
            "BancoDestino": self.get_banco(),
            "CuentaOrigen": self.cuenta_emisor,
            "Ordenante": self.nombre_emisor,
            "Monto": self.monto,
            "ConceptoPago": self.concepto_pago,
            "Referencia": self.referencia_numerica,
            "FechaOperación": self.date_modify,
            "Pago": self.tipo_pago.get_tipo_pago(),
            "Creado": "ND" if self.emisor_empresa is None else self.emisor_empresa.name,
            "Concepto": self.concepto_pago,
            "Modificado": self.auth_to(),
            "SaldoRemanente": self.saldo_remanente
        }

    @property
    def notification_detail(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tipo_pago_id": self.tipo_pago_id,
            "concepto_pago": self.concepto_pago,
            "referencia_numerica": self.referencia_numerica,
            "fecha_creacion": str(self.fecha_creacion),
            "monto": self.monto,
            "nombre_emisor": self.nombre_emisor,
            "cuenta_emisor": self.cuenta_emisor,
            "nombre_beneficiario": self.nombre_beneficiario,
            "cta_beneficiario": self.cta_beneficiario,
            "status_trans_id": self.status_trans_id,
            "tipo_pago": self.tipo_pago.nombre_tipo,
            "banco_emisor": self.transmitter_bank.institucion,
            "banco_beneficiario": self.receiving_bank.institucion,
            "status": self.status_trans.nombre,
        }


# (AntAboy) Tabla para guardar las transferenci
class transferenciaProg(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    transferReferida = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING, null=False, blank=False)
    fechaProgramada = models.DateTimeField(blank=False, null=False)
    fechaEjecucion = models.DateTimeField(blank=False, null=False)

    def get_transferencia_programada(self):
        return {
            "id": self.id,
            "transferReferida": self.transferReferida_id,
            "fechaProgramada": self.fechaProgramada
        }


# (AntAboy 2021-11-03) Tabla para guardar registro de las transferencias masivas programadas
class TransMasivaProg(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    masivaReferida = models.ForeignKey(transmasivaprod, on_delete=models.DO_NOTHING, null=False, blank=False)
    fechaProgramada = models.DateTimeField(blank=False, null=False)
    fechaEjecucion = models.DateTimeField(blank=False, null=False)
    objects = ManagerTransMasivaProg()

    def get_date_shedule(self):
        return {
            "date_shedule": self.fechaProgramada,
            "date_liberation": self.fechaEjecucion
        }

    def get_massive_id(self):
        return self.masivaReferida_id


# (AntAboy 2021-10-25) Tabla para guardar detalles extra de las transferencias devueltas o canceladas u otro estado
class detalleTransferencia(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    transferReferida = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING, null=False, blank=False)
    fecharegistro = models.DateTimeField(auto_now_add=True)
    detalleT = models.TextField(max_length=254, null=False, blank=False, default="por detallar")

    objects = ManagerDetalleTransferencia()

    def motivo(self):
        return self.detalleT
