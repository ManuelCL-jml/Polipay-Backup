from django.db import models
from django.contrib.auth.models import Group
from apps.contacts.models import CatOperaciones


class HistoricoGrupos(models.Model):
    # tabla para guardar movimientos relacionados con los grupos de permisos
    id = models.AutoField(primary_key=True, editable=False)
    fkGroup = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    fechaRegistro = models.DateTimeField(auto_now=True)
    movimiento = models.ForeignKey(CatOperaciones, on_delete=models.DO_NOTHING)

