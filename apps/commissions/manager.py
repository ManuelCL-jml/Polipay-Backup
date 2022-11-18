from decimal import Decimal
from typing import Dict, Union, Any, List

from django.db import models
from django.db.models import Q


class ManagerComission(models.Manager):

    def create_comission(self, **kwargs):
        return self.model(
            person_payer_id=kwargs.pop('pagador'),
            person_debtor_id=kwargs.pop('deudor'),
            commission_rel_id=kwargs.pop('comission_id'),
        ).save(using=self._db)

    def get_info_comission(self, owner: int) -> List[Dict[str, Any]]:
        return (
            super()
            .get_queryset()
            .select_related(
                'person_payer',
                'person_debtor',
                'commission_rel',
            )
            .filter(
                person_debtor_id=owner
            )
            .values(
                'id',
                'person_payer_id',
                'person_debtor_id',
                'commission_rel_id',
                'commission_rel__percent',
                'commission_rel__amount',
                'commission_rel__type_id',
                'commission_rel__type__type',
                'commission_rel__application_id',
                'commission_rel__servicio_id',
                'commission_rel__servicio__product_id',
                'commission_rel__servicio__service_id',
                'commission_rel__servicio__product__nombre',
                'commission_rel__servicio__service__nombre',
            )
        )

    def get_services_activate(self, owner: int) -> List[Dict[str, Any]]:
        return (
            super()
            .get_queryset()
            .select_related(
                'person_payer',
                'person_debtor',
                'commission_rel',
            )
            .filter(
                person_debtor_id=owner
            )
            .values_list(
                'commission_rel__servicio__service_id',
                flat=True
            )
        )

    def get_info_comission_manual(self, owner: int, service_id: int) -> Dict[str, Union[int, Decimal]]:
        return (
            super()
            .get_queryset()
            .select_related(
                'person_payer',
                'person_debtor',
                'commission_rel',
            )
            .filter(
                person_debtor_id=owner,
                commission_rel__servicio__service_id=service_id
            )
            .values(
                'id',
                'person_payer_id',
                'person_debtor_id',
                'commission_rel_id',
                'commission_rel__percent',
                'commission_rel__amount',
                'commission_rel__type_id',
                'commission_rel__application_id',
                'commission_rel__servicio_id',
                'commission_rel__servicio__product_id',
                'commission_rel__servicio__product__nombre',
                'commission_rel__servicio__service__nombre',
            ).first()
        )


class ManagerCommissionDetail(models.Manager):
    def create(self, **kwargs):
        instance = self.model(
            commission_id=kwargs.pop('comission'),
            transaction_rel_id=kwargs.pop('transaction'),
            mount=kwargs.pop('amount'),
            status_id=kwargs.pop('status'),
            payment_date=kwargs.pop('payment_date')
        )

        instance.save(using=self._db)
        return instance

    def create_object(self, **kwargs):
        return self.model(
            commission_id=kwargs.pop('comission'),
            transaction_rel_id=kwargs.pop('transaction'),
            mount=kwargs.pop('amount'),
            status_id=kwargs.pop('status'),
            payment_date=kwargs.pop('payment_date')
        )

    def commission_detail_list(self, **kwargs) -> List[Dict]:
        return (
            super()
            .get_queryset()
            .select_related(
                'status',
                'transaction_rel',
                'commission',
            )
            .filter(
                # Q(transaction_rel__fecha_creacion__date__gte=kwargs.get("start_date")) &
                # Q(transaction_rel__fecha_creacion__date__lte=kwargs.get("end_date")),
                status_id=kwargs.get("status"),
                transaction_rel__cuentatransferencia__persona_cuenta_id=kwargs.get("client_id")
            )
            .values(
                "id",
                "mount",
                "commission",
                "transaction_rel_id",
                "transaction_rel__cta_beneficiario",
                "transaction_rel__nombre_beneficiario",
                "transaction_rel__rfc_curp_beneficiario",
                "transaction_rel__referencia_numerica",
                "transaction_rel__empresa",
                "transaction_rel__monto",
                "transaction_rel__nombre_emisor",
                "transaction_rel__cuenta_emisor",
                "transaction_rel__rfc_curp_emisor",
                "transaction_rel__tipo_pago_id",
                "commission_record",
                "transaction_rel__cuentatransferencia_id",
                "commission__commission_rel__percent",
            )
        )


class ManagerCatCommission(models.Manager):
    def create_cat_comission(self, **kwargs) -> int:
        instance = self.model(
            percent=kwargs.pop('porcentaje'),
            amount=kwargs.pop('monto'),
            description=kwargs.pop('descripcion'),
            type_id=kwargs.pop('tipo_comission'),
            application_id=kwargs.pop('aplicacion'),
            servicio_id=kwargs.pop('servicio')
        )

        instance.save(using=self._db)
        return instance.id

    def update_cat_comission(self, comission_id: int, **kwargs):
        return (
            super()
            .get_queryset()
            .filter(id=comission_id).update(**kwargs)
        )
