import datetime as dt

from MANAGEMENT.Utils.utils import generate_clave_rastreo_with_uuid, remove_asterisk
from apps.users.management import *


def referencia(type: str):
    date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d%H%M%S")
    rand = random.randrange(1000, 9999)
    return f"REF{type}{date_time}{rand}"


class FilterTransaction(models.Manager):

    # (GhrGil 2022-02-05) Actualiza el campo folio_OpEF de STP
    def update_folio_operacion(self, clave_rastreo: str, folio_stp: str):
        return (
            super()
            .get_queryset()
            .filter(clave_rastreo=clave_rastreo)
            .update(folio_OpEF=folio_stp)
        )

    # (ChrGil 2022-01-18) Regresa un listado de objectos de transferencias
    def list_trasnfer_objs_massive(self, massive_id: int, type_page_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'tipo_pago',
                'masivo_trans'
            )
            .filter(
                masivo_trans_id=massive_id,
                tipo_pago_id=type_page_id
            )
        )

    # (ChrGil 2021-12-28) Regresa un listado de transacciones, con la información que solicita STP
    def get_info_transaction_stp(self, masivo_trans_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'masivo_trans',
                'transmitter_bank',
                'receiving_bank'
            )
            .filter(
                masivo_trans_id=masivo_trans_id
            )
            .values(
                'id',
                'clave_rastreo',
                'concepto_pago',
                'cta_beneficiario',
                'cuenta_emisor',
                'empresa',
                'receiving_bank__participante',
                'transmitter_bank__participante',
                'monto',
                'nombre_beneficiario',
                'nombre_emisor',
                'referencia_numerica',
                'rfc_curp_beneficiario',
                't_ctaBeneficiario',
                't_ctaEmisor',
                'rfc_curp_emisor',
                'tipo_pago',
                'cuentatransferencia__persona_cuenta__rfc'
            )
        )

    # (ChrGil 2021-12-28) Regresa un listado de transacciones, con la información que solicita STP
    def get_info_transaction_stp_individual(self, transaction_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'masivo_trans',
                'transmitter_bank',
                'receiving_bank'
            )
            .filter(
                id=transaction_id
            )
            .values(
                'id',
                'clave_rastreo',
                'concepto_pago',
                'cta_beneficiario',
                'cuenta_emisor',
                'empresa',
                'receiving_bank__participante',
                'transmitter_bank__participante',
                'monto',
                'nombre_beneficiario',
                'nombre_emisor',
                'referencia_numerica',
                'rfc_curp_beneficiario',
                't_ctaBeneficiario',
                't_ctaEmisor',
                'rfc_curp_emisor',
                'tipo_pago',
                'cuentatransferencia__persona_cuenta__rfc'
            ).first()
        )

    # (ChrGil 2021-12-01) Regresa el monto total de una transacción masiva
    def get_monto_total_masiva(self, massive_id: int) -> float:
        amount = (
            super()
            .get_queryset()
            .select_related('masivo_trans')
            .filter(
                masivo_trans_id=massive_id
            )
            .values_list('monto', flat=True)
        )

        total_price: float = sum(amount)
        return round(total_price, 2)

    # (ChrGil 2021-11-29) Regresa un objeto del modelo transferencia
    def get_objects_transfer(self, transfer_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'masivo_trans',
                'status_trans',
                'cuentatransferencia'
            )
            .get(id=transfer_id)
        )

    # (ChrGil 2021-11-22) Listar transacciones a terceros individuales por estado y filtrado de lado del cliente
    def list_individual_transactions(self, status_id: int, cuenta_emisor: str, beneficiario: str, date1, date2):
        if beneficiario == 'null':
            beneficiario = ''

        return (
            super()
            .get_queryset()
            .filter(
                tipo_pago_id=2,
                status_trans_id=status_id,
                masivo_trans_id__isnull=True,
                cuenta_emisor__exact=cuenta_emisor,
                nombre_beneficiario__icontains=beneficiario,
                date_modify__range=(date1, date2),
            )
            .values(
                'id',
                'nombre_beneficiario',
                'monto',
                'date_modify',
                'clave_rastreo',
            )
            .order_by('-date_modify')
        )

    # (ChrGil 2021-11-10) Mostra mas detalles del detallado de una transacción masiva
    def detail_massive_transaction_individual(self, transaction_id: int):
        return (
            super()
            .get_queryset()
            .get(
                id=transaction_id
            )
            .show_detail_transaction_massive()
        )

    # (ChrGil 2021-11-08) Actualizar masivamente los estados de transferencias a estado cancelada
    def update_massive_transaction(self, masivo_trans_id: int, status_id: int, user_auth: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'masivo_trans',
                'user_autorizada'
            )
            .filter(
                masivo_trans_id=masivo_trans_id
            )
            .update(
                status_trans_id=status_id,
                user_autorizada_id=user_auth,
                date_modify=dt.datetime.now()
            )
        )

    # (ChrGil 2021-11-07) Ver detalles de las transacciones masivas
    def detail_massive_transaction(self, massive_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'masivo_trans',
                'status_trans'
            )
            .filter(
                masivo_trans_id=massive_id,
                tipo_pago_id=2
            )
            .values(
                'id',
                'nombre_beneficiario',
                'monto',
                'clave_rastreo',
                'fecha_creacion',
                'status_trans_id',
                'cuentatransferencia__persona_cuenta_id',
                'tipo_pago_id',
                'status_trans__nombre'
            )
        )

    # (ChrGil 2021-11-07) regresa un listado de masivo_trans_id
    def list_only_massive_id(self, cuenta_id: int):
        massive: List = (
            super()
            .get_queryset()
            .select_related(
                'cuentatransferencia',
                'tipo_pago'
            )
            .filter(
                masivo_trans_id__isnull=False,
                cuentatransferencia_id=cuenta_id,
                tipo_pago_id=2
            )
            .values_list(
                'masivo_trans_id',
                flat=True
            )
        )

        list_sets_massive: List = list(set(massive))
        return list_sets_massive

    # (ChrGil 201-11-03) listado para mostrar los id de las masivas
    def list_massive_trans(self, masivo_trans_id: int):
        return (
            super()
            .get_queryset()
            .filter(
                masivo_trans_id=masivo_trans_id
            )
            .values(
                'cta_beneficiario',
                'monto'
            )
        )

    def detail_dispersion(self, transaction_id: int):
        return (
            super()
            .get_queryset()
            .get(
                id=transaction_id
            )
            .show_detail_dispersion()
        )

    def detail_transaction(self, transaction_id: int, status: int):
        return (
            super()
            .get_queryset()
            .get(
                id=transaction_id,
                status_trans_id=status
            )
            .show_detail_transaction()
        )

    def list_pending_transactions(self, transaction_id: int):
        return (
            super()
            .get_queryset()
            .get(
                id=transaction_id,
                status_trans_id__in=[3, 4]
            )
            .show_detail_transaction_pending()
        )

    # (ChrGil 2021-11-05) Listado de movimientos de dispersiones (ingresos y egresos)
    def list_income_and_expenses(self, cuenta: str, date1: datetime, date2: datetime):
        return (
            super()
            .get_queryset()
            .filter(
                Q(cuenta_emisor=cuenta) |
                Q(cta_beneficiario=cuenta),
                fecha_creacion__range=(date1, date2),
                tipo_pago_id=4
            )
            .values(
                'id',
                'nombre_beneficiario',
                'cta_beneficiario',
                'clave_rastreo',
                'concepto_pago',
                'monto',
                'saldo_remanente',
                'fecha_creacion',
                'referencia_numerica',
            )
            .order_by('-fecha_creacion')
        )

    # (ChrGil 2021-10-13) Filtro y listado de movimientos de ingresos de una cuenta eje
    def list_income(self, cuenta_beneficiario: str, date1, date2):
        return (
            super()
            .get_queryset()
            .filter(
                cta_beneficiario__icontains=cuenta_beneficiario,
                fecha_creacion__range=(date1, date2),
                tipo_pago_id=4,
            )
            .values(
                'id',
                'nombre_beneficiario',
                'cta_beneficiario',
                'clave_rastreo',
                'concepto_pago',
                'monto',
                'saldo_remanente',
                'fecha_creacion'
            )
            .order_by('-fecha_creacion')
        )

    # (ChrGil 2021-10-13) Filtro y listado de egresos de una cuenta eje
    def list_expenses(self, cuenta_emisor: str, date1, date2):
        return (
            super()
            .filter(
                cuenta_emisor=cuenta_emisor,
                fecha_creacion__range=(date1, date2),
                tipo_pago_id=4,
            )
            .values(
                'id',
                'nombre_beneficiario',
                'cta_beneficiario',
                'clave_rastreo',
                'concepto_pago',
                'monto',
                'saldo_remanente',
                'fecha_creacion',
            )
            .order_by('-fecha_creacion')
        )

    # (ChrGil 2021-10-12) Filtro y listado de transacciones recibidas
    def payment_type(self, nombre_emisor: str, date1, date2):
        return (
            super()
            .get_queryset()
            .select_related('tipo_pago', 'status_trans')
            .filter(
                tipo_pago_id=5,
                nombre_emisor__icontains=nombre_emisor,
                fecha_creacion__range=(date1, date2),
                status_trans_id=8
            )
            .values(
                'id',
                'nombre_beneficiario',
                'nombre_emisor',
                'monto',
                'clave_rastreo',
                'date_modify',
                'cta_beneficiario'
            )
        )

    # (ManuelCl 13-12-2021) Filtro para transacciones polipay a polipay enviadas
    def transactions_polipay_to_polipay_send(self, nombre_beneficiario: str, date1, date2, account_instance):
        if nombre_beneficiario == 'null':
            nombre_beneficiario = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
        if date2 == 'null':
            date2 = datetime.datetime.now()
        return (
            super()
            .get_queryset()
            .select_related('tipo_pago', 'status_trans')
            .filter(
                Q(cuenta_emisor=account_instance.cuenta) | Q(cuenta_emisor=account_instance.cuentaclave)
            )
            .filter(
                tipo_pago_id=1,
                nombre_beneficiario__icontains=nombre_beneficiario,
                fecha_creacion__range=(date1, date2),
                status_trans_id=1,
            )
            .values(
                'id',
                'nombre_beneficiario',
                'monto',
                'clave_rastreo',
                'fecha_creacion',
            )
            .order_by('-fecha_creacion')
        )

    # (ManuelCl 13-12-2021) Filtro para transacciones polipay a polipay recibidas
    def transactions_polipay_to_polipay_received(self, nombre_emisor: str, date1, date2, account_instance):
        print(account_instance.cuenta)
        if nombre_emisor == 'null':
            nombre_emisor = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
        if date2 == 'null':
            date2 = datetime.datetime.now()
        return (
            super()
            .get_queryset()
            .select_related('tipo_pago', 'status_trans')
            .filter(
                Q(cta_beneficiario=account_instance.cuenta) | Q(cta_beneficiario=account_instance.cuentaclave)
            )
            .filter(
                tipo_pago_id=1,
                nombre_emisor__icontains=nombre_emisor,
                fecha_creacion__range=(date1, date2),
                programada=False,
                status_trans_id__in=[1,9],
            )
            .values(
                'id',
                'nombre_emisor',
                'monto',
                'clave_rastreo',
                'fecha_creacion',
            )
            .order_by('-fecha_creacion')
        )

    # (ManuelCl 28-12-2021) Filtro para transacciones entre cuentas propias
    def transactions_own_accounts(self,empresa: str, date1, date2, account_instance: List[int]):
        if empresa == 'null':
            empresa = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
        if date2 == 'null':
            date2 = datetime.datetime.now()
        return (
            super()
            .get_queryset()
            .select_related('tipo_pago', 'status_trans')
            .filter(
                tipo_pago_id=7,
                empresa__icontains=empresa,
                fecha_creacion__range=(date1, date2),
                status_trans_id=1,
                cuenta_emisor__in=account_instance
            )
            .values(
                'id',
                'empresa',
                'nombre_beneficiario',
                'monto',
                'fecha_creacion',
            )
            .order_by('-fecha_creacion')
        )

    # (ManuelCalixtro 13/01/2022) Se creo metodo para listar las transacciones recibidas de personas morales con filtro
    def transactions_received_moral_person(self, nombre_emisor: str, tipo_persona_id: int, date1, date2):
        if nombre_emisor == 'null':
            nombre_emisor = ''
        if date1 == 'null':
            date1 = datetime.datetime.now() - datetime.timedelta(days=91)
        if date2 == 'null':
            date2 = datetime.datetime.now()
        return (
            super()
            .get_queryset()
            .select_related('tipo_pago', 'status_trans', 'cuentatransferencia')
            .filter(
                status_trans_id=1,
                cuentatransferencia__persona_cuenta__tipo_persona_id=tipo_persona_id,
                tipo_pago_id=5,
                nombre_emisor__icontains=nombre_emisor,
                fecha_creacion__range=(date1, date2),
            )
            .values(
                'id',
                'nombre_beneficiario',
                'nombre_emisor',
                'monto',
                'clave_rastreo',
                'date_modify',
                'cta_beneficiario',
                'cuentatransferencia__persona_cuenta__tipo_persona_id'
            )
            .order_by('-fecha_creacion')
        )

    # (ChrGil 2021-10-13) Filtro y listado para los estados individuales para personas fisicas y morales (Admin)
    # Modificado (ChrGil 2021-10-19) Se listan las transferencias individuales para personas fisicas y morales
    def transaction_individual_admin(self, id: int, status_type: int, nombre_beneficiario: str, date1, date2, clave_rastreo: str):
        if nombre_beneficiario == 'null':
            nombre_beneficiario = ''

        if clave_rastreo == 'null':
            clave_rastreo = ''

        return (
            super()
            .get_queryset()
            .filter(
                id__icontains=id,
                tipo_pago_id__in=[1, 2],
                status_trans_id=status_type,
                nombre_beneficiario__icontains=nombre_beneficiario,
                fecha_creacion__range=(date1, date2),
                clave_rastreo__icontains=clave_rastreo,
                user_autorizada__isnull=False
            )
            .values(
                'id',
                'empresa',
                'masivo_trans_id',
                'nombre_beneficiario',
                'cta_beneficiario',
                'monto',
                'clave_rastreo',
                'fecha_creacion',
                'status_trans_id'
            )
            .order_by('-fecha_creacion')
        )


class transferenciaManager(models.Manager):
    def create_transfer(self,
                        tipo_pago,
                        cta_beneficiario,
                        nombre_beneficiario,
                        transmitter_bank,
                        monto,
                        concepto_pago,
                        referencia_numerica,
                        nombre_emisor,
                        cuenta_emisor,
                        cuentatransferencia,
                        receiving_bank,
                        status_trans):
        clave_rastreo = 'PO' + str(Code_card(28))
        transfer = self.model(
            tipo_pago_id=tipo_pago,
            cta_beneficiario=cta_beneficiario,
            nombre_beneficiario=nombre_beneficiario,
            transmitter_bank_id=transmitter_bank,
            monto=monto,
            concepto_pago=concepto_pago,
            referencia_numerica=referencia_numerica,
            nombre_emisor=nombre_emisor,
            cuenta_emisor=cuenta_emisor,
            cuentatransferencia_id=cuentatransferencia,
            receiving_bank_id=receiving_bank,
            clave_rastreo=clave_rastreo,
            rfc_curp_beneficiario='N/A',
            tipo_cuenta='N/A',
            empresa='N/A',
            fecha_creacion=dt.datetime.now(),
            date_modify=dt.datetime.now(),
            status_trans_id=status_trans
        )
        transfer.save(force_insert=True, using=self._db)
        return transfer

    # Modificado (ChrGil 2021-11-19) Se modifica el campo banco_beneficiario a banco_beneficiario_id y
    # Modificado (ChrGil 2021-11-19) el campo banco_emisor a banco_emisor_id
    def create_disper(self, cta_beneficiario, nombre_beneficiario, monto, concepto_pago, is_schedule, nombre_emisor,
                      cuenta_emisor, cuentatransferencia_id, masivo_trans_id, saldo_remanente=None, empresa=None):
        clave_rastreo = 'PO' + str(Code_card(28))

        saldo_remanente -= monto
        dispersion = self.model(
            cta_beneficiario=cta_beneficiario,
            nombre_beneficiario=nombre_beneficiario,
            monto=monto,
            concepto_pago=concepto_pago,
            referencia_numerica=referencia('DIS'),
            empresa=empresa,
            nombre_emisor=nombre_emisor,
            cuenta_emisor=cuenta_emisor,
            cuentatransferencia_id=cuentatransferencia_id,
            receiving_bank_id=86,
            clave_rastreo=clave_rastreo,
            date_modify=dt.datetime.now(),
            programada=is_schedule,
            fecha_creacion=dt.datetime.now(),
            tipo_pago_id=4,
            rfc_curp_beneficiario='S/E',
            tipo_cuenta='S/E',
            transmitter_bank_id=86,
            masivo_trans_id=masivo_trans_id,
            saldo_remanente=saldo_remanente
        )
        dispersion.save(using=self._db)

        return dispersion

    def create_trans_rec(self, empresa, nombre_emisor, transmitter_bank_id, cuenta_emisor, monto, concepto_pago,
                         referencia_numerica,
                         clave_rastreo, nombre_beneficiario, cta_beneficiario, cuentatransferencia_id, date_modify):
        trans_rec = self.model(
            empresa=empresa,
            nombre_emisor=nombre_emisor,
            transmitter_bank_id=transmitter_bank_id,
            cuenta_emisor=cuenta_emisor,
            monto=monto,
            concepto_pago=concepto_pago,
            referencia_numerica=referencia_numerica,
            clave_rastreo=clave_rastreo,
            fecha_creacion=dt.datetime.now(),
            nombre_beneficiario=nombre_beneficiario,
            cta_beneficiario=cta_beneficiario,
            cuentatransferencia_id=cuentatransferencia_id,
            date_modify=date_modify,
            tipo_pago_id=5,
            status_trans_id=1,
            rfc_curp_beneficiario='S/E',
            receiving_bank_id=86,
            tipo_cuenta='S/E',
        )

        trans_rec.save(using=self._db)
        return trans_rec

    # (ChrGil 2022-02-02) Crea transacción a terceros individuales
    def create_transaction_individual(self, **kwargs):
        transfer = self.model(
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            nombre_beneficiario=kwargs.pop("nombre_beneficiario"),
            email=kwargs.pop("email"),
            rfc_curp_beneficiario=kwargs.pop("rfc_curp_beneficiario"),
            cta_beneficiario=kwargs.pop("cuenta_beneficiario"),
            t_ctaBeneficiario=kwargs.pop("tipo_cuenta_beneficiario"),
            monto=kwargs.pop("monto"),
            receiving_bank_id=kwargs.pop("banco_beneficiario_id"),
            referencia_numerica=kwargs.pop("referencia_numerica"),
            concepto_pago=kwargs.pop("concepto_pago"),
            nombre_emisor=kwargs.pop("nombre_emisor"),
            cuenta_emisor=kwargs.pop("cuenta_emisor"),
            cuentatransferencia_id=kwargs.pop("cuenta_id"),
            emisor_empresa_id=kwargs.pop("emisor_empresa_id"),
            empresa=kwargs.pop("empresa"),
            transmitter_bank_id=86,
            date_modify=dt.datetime.now(),
            tipo_pago_id=2,
            tipo_cuenta='S/E',
            status_trans_id=3,
            t_ctaEmisor=40
        )

        transfer.save(using=self._db)
        return transfer

    def trans_rec_saldos(self, nombre_beneficiario, cta_beneficiario, referencia, monto, saldo_remanente,
                         fecha_creacion):
        clave_rastreo = 'PO' + str(Code_card(28))
        date_now = datetime.date.today()

        saldos = self.model(
            cta_beneficiario=cta_beneficiario,
            nombre_beneficiario=nombre_beneficiario,
            monto=monto,
            concepto_pago=f'Saldo Dispersión - {referencia}',
            empresa='S/E',
            nombre_emisor='Solicitud de Saldos',
            cuenta_emisor='S/E',
            receiving_bank_id=86,
            clave_rastreo=clave_rastreo,
            date_modify=datetime.datetime.now(),
            tipo_pago_id=4,
            rfc_curp_beneficiario='S/E',
            tipo_cuenta='S/E',
            transmitter_bank_id=86,
            saldo_remanente=saldo_remanente,
            fecha_creacion=fecha_creacion,
            referencia_numerica=f'{date_now.day}{date_now.month}{date_now.year}0'
        )

        saldos.save(using=self._db)

        return saldos

    def transferencia_terceros_saldos(self, nombre_emisor, cuenta_emisor, referencia, monto, saldo_remanente):
        clave_rastreo = 'PO' + str(Code_card(28))
        date_now = datetime.date.today()

        saldos = self.model(
            cta_beneficiario='S/E',
            nombre_beneficiario='Polipay Comision',
            monto=monto,
            concepto_pago=f'Comisión Dispersión - {referencia}',
            empresa='S/E',
            nombre_emisor=nombre_emisor,
            cuenta_emisor=cuenta_emisor,
            receiving_bank_id=86,
            clave_rastreo=clave_rastreo,
            tipo_pago_id=4,
            rfc_curp_beneficiario='S/E',
            tipo_cuenta='S/E',
            transmitter_bank_id=86,
            saldo_remanente=saldo_remanente,
            referencia_numerica=f'{date_now.day}{date_now.month}{date_now.year}1',
            date_modify=datetime.datetime.now()

        )

        saldos.save(using=self._db)

        return saldos

    def create_transaction_polipay_to_polipay(self, nombre_beneficiario, cuenta_emisor, cta_beneficiario, monto,
                                              concepto_pago, referencia_numerica, email, rfc_curp_beneficiario,
                                              empresa, nombre_emisor):
        clave_rastreo = 'PO' + str(Code_card(28))

        trans_polipay = self.model(
            empresa=empresa,
            nombre_emisor=nombre_emisor,
            transmitter_bank_id=86,
            cuenta_emisor=cuenta_emisor,
            monto=monto,
            concepto_pago=concepto_pago,
            referencia_numerica=referencia_numerica,
            clave_rastreo=clave_rastreo,
            fecha_creacion=dt.datetime.now(),
            nombre_beneficiario=nombre_beneficiario,
            cta_beneficiario=cta_beneficiario,
            date_modify=dt.datetime.now(),
            tipo_pago_id=1,
            rfc_curp_beneficiario=rfc_curp_beneficiario,
            receiving_bank_id=86,
            tipo_cuenta='S/E',
            email=email,
            status_trans_id=1,

            # emisor_empresa_id=emisor_empresa_id,
        )

        trans_polipay.save(using=self._db)

        return trans_polipay

    def create_transaction_to_return_comission(self, monto, nombre_beneficiario, cta_beneficiario, rfc_curp_beneficiario):
        clave_rastreo = 'PO' + str(Code_card(28))

        trans_polipay = self.model(
            empresa='POLIPAY COMISSION',
            nombre_emisor='POLIPAY COMISSION',
            transmitter_bank_id=86,
            cuenta_emisor=646180171802500018,
            monto=monto,
            concepto_pago="Devolucion de Comision por Dispercion Cancelada",
            referencia_numerica=Code_card(7),
            clave_rastreo=clave_rastreo,
            fecha_creacion=dt.datetime.now(),
            nombre_beneficiario=nombre_beneficiario,
            cta_beneficiario=cta_beneficiario,
            date_modify=dt.datetime.now(),
            tipo_pago_id=1,
            rfc_curp_beneficiario=rfc_curp_beneficiario,
            receiving_bank_id=86,
            tipo_cuenta='S/E',
            status_trans_id=1,
        )

        trans_polipay.save(using=self._db)

        return trans_polipay

    def create_movement_to_return_dispersion(self, cuenta_emisor, cta_beneficiario, monto, nombre_beneficiario, nombre_emisor):
        clave_rastreo = 'PO' + str(Code_card(28))

        trans_polipay = self.model(
            empresa=nombre_beneficiario,
            nombre_emisor=nombre_emisor,
            transmitter_bank_id=86,
            cuenta_emisor=cuenta_emisor,
            monto=monto,
            concepto_pago="Devolucion por Dispercion Cancelada",
            referencia_numerica=Code_card(7),
            clave_rastreo=clave_rastreo,
            fecha_creacion=dt.datetime.now(),
            nombre_beneficiario=nombre_beneficiario,
            cta_beneficiario=cta_beneficiario,
            date_modify=dt.datetime.now(),
            tipo_pago_id=1,
            receiving_bank_id=86,
            tipo_cuenta='S/E',
            status_trans_id=1,
        )

        trans_polipay.save(using=self._db)

        return trans_polipay

    def create_movement_to_return_massive_dispersion(self, dispersion):
        clave_rastreo = 'PO' + str(Code_card(28))
        for data in dispersion:
            create_dispesion = self.model(
                nombre_emisor=data['nombre_beneficiario'],
                cuenta_emisor=data['cta_beneficiario'],
                cta_beneficiario=data['cuenta_emisor'],
                nombre_beneficiario=data['nombre_emisor'],
                clave_rastreo=clave_rastreo,
                monto=data['monto'],
                rfc_curp_emisor=data['rfc_curp_emisor'],
                concepto_pago="Devolucion dispersion cancelada",
                fecha_creacion=datetime.datetime.now(),
                date_modify=datetime.datetime.now(),
                referencia_numerica=Code_card(7),
                empresa=data['nombre_beneficiario'],
                tipo_pago_id=1,
                programada=data['programada'],
                masivo_trans_id=data['masivo_trans_id'],
                status_trans_id=1
            )
            create_dispesion.save(using=self._db)
            return create_dispesion

    def create_transaction_to_return_massive_comission(self, monto_total, cuenta):
        clave_rastreo = 'PO' + str(Code_card(28))
        trans_polipay = self.model(
            empresa='POLIPAY COMISSION',
            nombre_emisor='POLIPAY COMISSION',
            transmitter_bank_id=86,
            cuenta_emisor=646180171802500018,
            monto=monto_total,
            concepto_pago="Devolucion de Comision por Dispercion Cancelada",
            referencia_numerica=Code_card(7),
            clave_rastreo=clave_rastreo,
            fecha_creacion=dt.datetime.now(),
            nombre_beneficiario=cuenta.persona_cuenta.name,
            cta_beneficiario=cuenta.cuenta,
            date_modify=dt.datetime.now(),
            tipo_pago_id=1,
            receiving_bank_id=86,
            tipo_cuenta='S/E',
            status_trans_id=1,
        )

        trans_polipay.save(using=self._db)
        return trans_polipay

    def create_transaction_polipay_to_polipay_v2(self, **kwargs):
        instance = self.model(
            empresa=kwargs.get("empresa"),
            cuenta_emisor=kwargs.get("cuenta_emisor"),
            nombre_emisor=kwargs.get("nombre_emisor"),
            rfc_curp_emisor=kwargs.get("rfc_curp_emisor"),
            monto=kwargs.get("monto"),
            concepto_pago=kwargs.get("concepto_pago"),
            referencia_numerica=kwargs.get("referencia_numerica"),
            nombre_beneficiario=kwargs.get("nombre_beneficiario"),
            cta_beneficiario=kwargs.get("cta_beneficiario"),
            rfc_curp_beneficiario=kwargs.get("rfc_curp_beneficiario"),
            emisor_empresa_id=kwargs.get("create_to"),
            cuentatransferencia_id=kwargs.get("cuentatransferencia_id"),
            email=kwargs.get("email", "ND"),
            saldo_remanente=kwargs.get("saldo_remanente"),
            t_ctaEmisor=40,
            transmitter_bank_id=86,
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            fecha_creacion=dt.datetime.now(),
            t_ctaBeneficiario=40,
            date_modify=dt.datetime.now(),
            tipo_pago_id=kwargs.get("tipo_pago_id", 1),
            receiving_bank_id=86,
            status_trans_id=3,
        )
        instance.save(using=self._db)
        return instance

    def create_trans_own_accounts(self, empresa, nombre_beneficiario, nombre_emisor, concepto_pago, monto,
                                  cuenta_emisor, cta_beneficiario, cuentatransferencia_id, emisor_empresa_id):
        clave_rastreo = 'PO' + str(Code_card(28))
        trans_own_accounts = self.model(
            empresa=empresa,
            nombre_beneficiario=nombre_beneficiario,
            nombre_emisor=nombre_emisor,
            concepto_pago=concepto_pago,
            monto=monto,
            cuenta_emisor=cuenta_emisor,
            cta_beneficiario=cta_beneficiario,
            status_trans_id=1,
            fecha_creacion=datetime.datetime.now(),
            date_modify=datetime.datetime.now(),
            transmitter_bank_id=86,
            receiving_bank_id=86,
            tipo_pago_id=7,
            referencia_numerica='S/E',
            clave_rastreo=clave_rastreo,
            cuentatransferencia_id=cuentatransferencia_id,
            emisor_empresa_id=emisor_empresa_id
        )
        trans_own_accounts.save(using=self._db)
        return trans_own_accounts

    # (ChrGil 2021-12-30) El banco operante siempre va a ser Polipay (90904) y su id es 86
    # (ChrGil 2021-11-03) Metodo que se encarga de crear el objeto para cada transferencia individual
    def create_object_transfer(self, **kwargs):
        return self.model(
            receiving_bank_id=kwargs.get("institucionContraparte"),
            empresa=kwargs.get("empresa"),
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            monto=kwargs.get("monto"),
            nombre_emisor=kwargs.get("nombreOrdenante"),
            cuenta_emisor=kwargs.get("cuentaOrdenante"),
            t_ctaBeneficiario=kwargs.get("tipoCuentaBeneficiario"),
            nombre_beneficiario=kwargs.get("nombreBeneficiario"),
            cta_beneficiario=kwargs.get("cuentaBeneficiario"),
            rfc_curp_beneficiario=kwargs.get("rfcCurpBeneficiario"),
            concepto_pago=kwargs.get("conceptoPago"),
            referencia_numerica=kwargs.get("referenciaNumerica"),
            programada=kwargs.get('programada', False),
            emisor_empresa_id=kwargs.get("emisor_empresa_id", None),
            masivo_trans_id=kwargs.get("masivo_trans_id", None),
            cuentatransferencia_id=kwargs.get("cuentatransferencia_id"),
            rfc_curp_emisor=kwargs.get('rfc_curp_emisor'),
            tipo_pago_id=2,
            t_ctaEmisor=40,
            transmitter_bank_id=86,
            status_trans_id=3,
            email='S/E',
            date_modify=datetime.datetime.now()
        )

    # (ChrGil 2022-01-24) Metodo que crea una transacción a POLIPAY COMISSION
    def tranfer_to_polipay_comission(self, **kwargs):
        transfer = self.model(
            empresa=kwargs.get("empresa", 'N/A'),
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            monto=kwargs.pop("monto"),
            nombre_emisor=kwargs.pop("nombre_emisor"),
            cuenta_emisor=kwargs.pop("cuenta_emisor"),
            rfc_curp_emisor=kwargs.pop("rfc_curp_emisor", 'N/A'),
            nombre_beneficiario=kwargs.pop("nombre_beneficiario"),
            cta_beneficiario=kwargs.pop("cta_beneficiario"),
            rfc_curp_beneficiario=kwargs.pop("rfc_curp_beneficiario", 'N/A'),
            referencia_numerica=dt.datetime.strftime(dt.datetime.now(), "%y%m%d"),
            cuentatransferencia_id=kwargs.pop("cuentatransferencia_id"),
            status_trans_id=kwargs.get('status_trans_id', 1),
            saldo_remanente=kwargs.get('saldo_remanente', 0.0),
            saldo_remanente_beneficiario=kwargs.get('saldo_remanente_beneficiario', 0.0),
            t_ctaBeneficiario=40,
            t_ctaEmisor=40,
            concepto_pago=kwargs.get('concepto_pago', "POLIPAY COMISIONES"),
            transmitter_bank_id=86,
            receiving_bank_id=86,
            tipo_pago_id=1,
            email='S/E',
            date_modify=datetime.datetime.now()
        )
        transfer.save(using=self._db)
        return transfer

    # (ChrGil 2022-01-24) Crear una transacción recibida STP
    def create_transaction_received(self, **kwargs) -> int:
        transfer = self.model(
            folio_OpEF=kwargs.pop('id'),
            transmitter_bank_id=kwargs.pop('institucionOrdenante'),
            receiving_bank_id=kwargs.pop('institucionBeneficiaria'),
            clave_rastreo=kwargs.pop('claveRastreo'),
            monto=kwargs.get('monto'),
            nombre_emisor=kwargs.pop('nombreOrdenante'),
            t_ctaEmisor=kwargs.pop('tipoCuentaOrdenante'),
            cuenta_emisor=kwargs.pop('cuentaOrdenante'),
            rfc_curp_emisor=kwargs.pop('rfcCurpOrdenante'),
            nombre_beneficiario=kwargs.pop('nombreBeneficiario'),
            t_ctaBeneficiario=kwargs.pop('tipoCuentaBeneficiario'),
            cta_beneficiario=kwargs.pop('cuentaBeneficiario'),
            rfc_curp_beneficiario=kwargs.pop('rfcCurpBeneficiario'),
            concepto_pago=kwargs.pop('conceptoPago'),
            referencia_numerica=kwargs.pop('referenciaNumerica'),
            empresa=kwargs.pop('empresa'),
            cuentatransferencia_id=kwargs.pop('cuentatransferencia_id'),
            saldo_remanente=kwargs.get('saldo_remanente', None),
            saldo_remanente_beneficiario=kwargs.get('saldo_remanente_beneficiario', None),
            status_trans_id=1,
            tipo_pago_id=kwargs.get('tipo_pago_id', 5),
            date_modify=dt.datetime.now()
        )

        transfer.save(using=self._db)
        return transfer

    # (ChrGil 2022-01-24) Crear una transacción recibida STP
    def create_transaction_received_manual(self, **kwargs) -> int:
        transfer = self.model(
            transmitter_bank_id=kwargs.pop('institucionOrdenante'),
            receiving_bank_id=kwargs.pop('institucionBeneficiaria'),
            clave_rastreo=kwargs.pop('claveRastreo'),
            monto=kwargs.pop('monto'),
            nombre_emisor=kwargs.pop('nombreOrdenante'),
            t_ctaEmisor=kwargs.pop('tipoCuentaOrdenante'),
            cuenta_emisor=kwargs.pop('cuentaOrdenante'),
            nombre_beneficiario=kwargs.pop('nombreBeneficiario'),
            t_ctaBeneficiario=kwargs.pop('tipoCuentaBeneficiario'),
            cta_beneficiario=kwargs.pop('cuentaBeneficiario'),
            rfc_curp_beneficiario=kwargs.pop('rfcCurpBeneficiario'),
            concepto_pago=kwargs.pop('conceptoPago'),
            referencia_numerica=kwargs.pop('referenciaNumerica'),
            empresa=kwargs.pop('empresa'),
            cuentatransferencia_id=kwargs.pop('cuentatransferencia_id'),
            # saldo_remanente=kwargs.pop('saldo_remanente'),
            status_trans_id=1,
            tipo_pago_id=5,
            date_modify=dt.datetime.now()
        )
        transfer.save(using=self._db)
        return transfer.id

    # (ChrGil 2022-01-03) Se crea un objeto para crear una dispersión masiva
    def create_object_dispersion(self, **kwargs):
        return self.model(
            cta_beneficiario=kwargs.pop("account"),
            nombre_beneficiario=remove_asterisk(kwargs.pop("name")),
            monto=kwargs.pop("amount"),
            email=kwargs.pop("mail"),
            concepto_pago=kwargs.pop("concepto_pago"),
            empresa=kwargs.pop("empresa"),
            referencia_numerica=kwargs.pop("referencia_numerica"),
            programada=kwargs.pop("programada"),
            nombre_emisor=kwargs.pop("nombre_emisor"),
            cuenta_emisor=kwargs.pop("cuenta_emisor"),
            cuentatransferencia_id=kwargs.pop("cuentatransferencia_id"),
            masivo_trans_id=kwargs.pop("masivo_trans_id"),
            emisor_empresa_id=kwargs.pop("emisor_empresa_id"),
            receiving_bank_id=86,
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            tipo_pago_id=4,
            tipo_cuenta="ND",
            rfc_curp_beneficiario="ND",
            transmitter_bank_id=86,
            status_trans_id=3,
            date_modify=datetime.datetime.now()
        )

    # (ChrGil 2022-05-09) Transacción
    def create_transaction_red_efectiva(self, **kwargs):
        transfer = self.model(
            concepto_pago=f"{kwargs.get('tipo')} {kwargs.get('nombre_servicio')}",
            nombre_beneficiario=kwargs.get('nombre_servicio'),
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            cuentatransferencia=kwargs.pop('cuenta'),
            referencia_numerica=kwargs.pop('referencia'),
            nombre_emisor=kwargs.pop('nombre_emisor'),
            cuenta_emisor=kwargs.pop('cuenta_emisor'),
            empresa=kwargs.get("empresa", "N/A"),
            cta_beneficiario='8960010002',
            rfc_curp_beneficiario='N/A',
            monto=kwargs.pop('monto'),
            transmitter_bank_id=86,
            t_ctaBeneficiario=40,
            receiving_bank_id=86,
            status_trans_id=1,
            t_ctaEmisor=40,
            tipo_pago_id=8,
            date_modify=dt.datetime.now()
        )

        transfer.save(using=self._db)
        return transfer

    def create_internal_movement(self, **kwargs):
        instance = self.model(
            saldo_remanente_beneficiario=kwargs.get("saldo_remanente_beneficiario", 0.0),
            cuentatransferencia_id=kwargs.get("cuentatransferencia_id"),
            nombre_beneficiario=kwargs.get("nombre_beneficiario"),
            referencia_numerica=kwargs.get("referencia_numerica"),
            cta_beneficiario=kwargs.get("cuenta_beneficiario"),
            clave_rastreo=generate_clave_rastreo_with_uuid(),
            rfc_curp_beneficiario=kwargs.get("rfc", "ND"),
            concepto_pago=kwargs.get("concepto_pago"),
            nombre_emisor=kwargs.get("nombre_emisor"),
            cuenta_emisor=kwargs.get("cuenta_emisor"),
            tipo_pago_id=kwargs.get("tipo_pago_id"),
            monto=kwargs.get("monto"),
            email=kwargs.get("email"),
            empresa="NA",
            programada=False,
            masivo_trans_id=None,
            emisor_empresa_id=None,
            receiving_bank_id=86,
            tipo_cuenta="ND",
            transmitter_bank_id=86,
            status_trans_id=1,
            date_modify=datetime.datetime.now()
        )

        instance.save(using=self._db)
        return instance


# (ChrGil 2021-11-01) Manager para las transferencias masivas
class TransferenciaMasivaManager(models.Manager):
    # (ChrGil 2021-11-01) Metodo para crear una transferencia masiva
    def create_transaction_massive(self, observations: str, status: int, user_admin_id: int):
        massive = self.model(observations=observations, statusRel_id=status, usuarioRel_id=user_admin_id)
        massive.date_modified = datetime.datetime.now()
        massive.date_liberation = datetime.datetime.now()
        massive.save(using=self._db)
        return massive

    # (ChrGil 2021-11-07) Listar transacciones masivas con filtro
    def list_massive(self, list_massive_id: List[int], status_id: int, start_date, end_date, observations: str = ''):
        return (
            super()
            .get_queryset()
            .select_related(
                'statusRel'
            )
            .filter(
                id__in=list_massive_id,
                statusRel_id=status_id,
                observations__icontains=observations,
                date_created__range=(start_date, end_date)
            )
            .values(
                'id',
                'observations',
                'date_modified',
                'usuarioRel__name',
                'usuarioRel__last_name'
            )
            .order_by('-date_modified')
        )

    # (ChrGil 2021-11-08) Detalla la información de una transacción masiva
    def detail_info_transaction_massive(self, massive_id: int):
        return (
            super()
            .get_queryset()
            .get(
                id=massive_id
            )
            .get_detail_info()
        )

    # (ChrGil 2021-11-08) Cambia el estado de todas las transacciones masivas
    def change_status_massive(self, massive_id: int, status_id: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'statusRel'
            )
            .filter(
                id=massive_id
            )
            .update(
                statusRel_id=status_id,
                date_modified=dt.datetime.now()
            )
        )

    def get_object_transmassive(self, massive_trans):
        return (
            super()
            .get_queryset()
            .select_related(
                "statusRel",
                "usuarioRel"
            )
            .get(
                id=massive_trans
            )
        )


# (ChrGil 2021-11-08) Manager del modelo TransMasivaProg
class ManagerTransMasivaProg(models.Manager):

    # (ChrGil 2021-11-29) Devuelve True o False si la transacción es programada
    def transaction_is_shedule(self, massive_id: int):
        return (
            super()
            .get_queryset()
            .select_related('masivaReferida')
            .filter(
                masivaReferida_id=massive_id
            )
            .exists()
        )

    # (ChrGil 2021-12-03) Regresa una instancia del modelo TransMasivaProg
    def get_object_trans_masiva_prog(self, massive_id: int):
        return (
            super()
            .get_queryset()
            .select_related('masivaReferida')
            .get(
                masivaReferida_id=massive_id
            )
        )


# (ChrGil 2022-02-01) Crear el detalle de una transferencia
class ManagerDetalleTransferencia(models.Manager):
    def create(self, **kwargs):
        self.model(
            transferReferida_id=kwargs.pop('transfer_id'),
            detalleT=kwargs.pop('json_content')
        ).save(using=self._db)