from typing import Any, Dict

from django.db import models
import json

from django.db.models import Q


class ManagerCatProductsParams(models.Manager):
    def create_params(self, **kwargs):
        instance = self.model(
            supplier_id=kwargs.get("proveedor_id"),
            json_content=json.dumps(kwargs.get("response"))
        )

        instance.save(using=self._db)


class ManagerCatSupplier(models.Manager):
    def get_supplier(self, name: str, short_name: str) -> Dict[str, Any]:
        return (
            super()
            .filter(
                Q(name_short__icontains=name) |
                Q(name_large__icontains=short_name)
            ).values(
                "id"
            ).first()
        )
