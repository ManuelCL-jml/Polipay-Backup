from typing import Dict, Any, Union
import datetime as dt
from django.db import models


class ManagerUserToken(models.Manager):
    # (ChrGil 2022-01-17) Regresa una booleano si el token esta activo o no
    def get_last_dynamic_token(self, owner: int) -> Dict[str, Union[bool, dt.datetime, str]]:
        return (
            super()
            .get_queryset()
            .select_related('person_id')
            .filter(
                person_id=owner,
                is_active=True
            )
            .values('is_active', 'effective_date', 'json_content')
            .last()
        )

    def change_status_dynamic_token(self, owner: int):
        return (
            super()
            .get_queryset()
            .filter(
                person_id=owner
            )
            .update(is_active=False)
        )

    # (ChrGil 2022-01-18) Regresa un diccionario de datos con el token encriptado
    def get_encryption_token(self, owner: int) -> Dict[str, Union[str, str]]:
        return (
            super()
            .get_queryset()
            .select_related(
                'person_id'
            )
            .filter(
                person_id_id=owner
            )
            .values(
                'token',
                'effective_date'
            )
            .last()
        )

    def update_user_token(self, owner: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'person_id'
            )
            .filter(
                person_id_id=owner,
                is_active=True
            )
            .update(is_active=False)
        )