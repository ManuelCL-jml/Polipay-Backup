from django.db import models


class ManagerLogEfectiva(models.Manager):
    def create_object(self, **kwargs):
        return self.model(
            folio=kwargs.get("folio"),
            autorization=kwargs.get("autorization"),
            ticket=kwargs.get("ticket"),
            correspondent=kwargs.get("correspondent"),
            transmitterid=kwargs.get("transmitterid"),
            reference_one=kwargs.get("reference_one"),
            amount=kwargs.get("amount"),
            commission=kwargs.get("commission"),
            charge=kwargs.get("charge"),
            code_id=kwargs.get("code_id"),
            transmitter_rel_id=kwargs.get("transmitter_rel_id"),
            user_rel_id=kwargs.get("user_rel_id")
        )