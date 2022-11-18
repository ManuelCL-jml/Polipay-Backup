from django.db import models


# (ChrGil 2022-01-12) Manager, para la creació de consultas personalizadas
class NotificationManager(models.Manager):
    def get_number_notification(self, owner: int):
        return (
            super()
            .get_queryset()
            .select_related(
                'person'
            )
            .filter(
                person_id=owner,
                is_active=True,
                deactivation_date__isnull=True,
                notification_type_id=1
            )
            .count()
        )
