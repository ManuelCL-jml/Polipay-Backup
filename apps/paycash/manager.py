from typing import Dict, Any, List

from django.db import models
from django.db.models import Q


class ManagerPayCashReference(models.Manager):
    def update_reference(self, reference_id: int, **kwargs):
        return (
            super()
            .get_queryset()
            .filter(
                id=reference_id
            )
            .update(
                **kwargs
            )
        )

    def detail_reference(self, reference_id: int) -> Dict[str, Any]:
        return (
            super()
            .get_queryset()
            .filter(
                id=reference_id
            )
            .values(
                "id",
                "amount",
                "date_cancel",
                "date_created",
                "payment_concept",
                "reference_number",
                "status_reference_id",
                "supplier__name_large",
                "status_reference__nombre",
                "persona_cuenta__cuentaclave",
                "type_reference__type_reference",
            )
            .first()
        )

    def list_reference(self, **kwargs) -> List[Dict[str, Any]]:
        return (
            super()
            .get_queryset()
            .filter(
                Q(date_created__date__gte=kwargs.get("start_date")) &
                Q(date_created__date__lte=kwargs.get("end_date"))
            )
            .filter(
                persona_cuenta__persona_cuenta_id=kwargs.get("user"),
                status_reference_id__in=list(kwargs.get("status"))
            )
            .values(
                "id",
                "amount",
                "reference_number",
                "payment_concept",
                "date_modify",
                "type_reference_id",
                "type_reference__type_reference",
                "status_reference_id",
                "status_reference__nombre",
                "value"
            )
            .order_by("-date_modify")
        )

    def detail_reference_with_value(self, value: str) -> Dict[str, Any]:
        return (
            super()
            .get_queryset()
            .select_related(
                "persona_cuenta"
            )
            .filter(
                value=value
            )
            .values(
                "id",
                "comission_pay",
                "payment_concept",
                "persona_cuenta_id",
                "type_reference_id",
                "status_reference_id",
                "persona_cuenta__persona_cuenta_id",
                "persona_cuenta__persona_cuenta__name",
                "persona_cuenta__persona_cuenta__rfc",
                "persona_cuenta__persona_cuenta__email",
                "persona_cuenta__persona_cuenta__token_device",
                "persona_cuenta__cuenta"
            )
            .last()
        )
