from django.db import models

from apps.notifications.manager import NotificationManager
from apps.transaction.models import transferencia
from apps.users.models import persona


# catalogo / tipo de notificaciones
class Cat_Notification(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=255)
    creation_data = models.DateTimeField(auto_now_add=True)


# notificaciones por usuario
class notification(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    person = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    notification_type = models.ForeignKey(Cat_Notification, on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deactivation_date = models.DateTimeField(null=True)
    json_content = models.TextField(max_length=None)
    transaction = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING, null=True, default=None)
    objects = NotificationManager()

# Aviso general para todos los usuarios, solo un registro debe estar en True
class general_advise(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    active = models.BooleanField(default=False, )
    tittle = models.CharField(max_length=50)
    message = models.TextField(max_length=None)
    creation_date = models.DateTimeField(auto_now_add=True)
    btn_login = models.BooleanField(default=True)
