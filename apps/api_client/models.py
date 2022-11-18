from django.db import models
from apps.users.models import cuenta, persona
import uuid
from .manager import *


# Create your models here.
class CredencialesAPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=30)
    password = models.CharField(max_length=255)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    personaRel = models.ForeignKey(persona, on_delete=models.DO_NOTHING, null=True, blank=True)
    # cuenta = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING) se cambia a persona
    objects = CredentialsManager()


