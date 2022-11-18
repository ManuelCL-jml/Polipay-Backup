from django.db import models

from apps.api_dynamic_token.manager import ManagerUserToken
from apps.users.models import persona


# Modelo donde tendremos un catalogo (tipos) de token, por el momento el unico es el dinamico.
class Cat_type_token(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=30, null=True, default=None)
    description = models.CharField(max_length=254, null=True, default=None)


#  Modelo en donde se registraran los token generados para los usuarios
class User_token(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=50, null=True, default=None)
    json_content = models.TextField(max_length=None)
    is_active = models.BooleanField(default=False)
    effective_date = models.DateTimeField(null=False, blank=False)
    person_id = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    token_related = models.ForeignKey(Cat_type_token, on_delete=models.DO_NOTHING)

    objects = ManagerUserToken()


# # Modelo donde estará configuracion adicional para generar el token, como el tiempo de vigencia
class Token_detail(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    time_config = models.IntegerField(default=3)
    person_id = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
