from django.db import models

from apps.contacts.manager import ManagerContacts, ManagerGroupContact
from apps.users.models import *
from apps.transaction.models import *


class contactos(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=45, null=False, blank=False)
    cuenta = models.CharField(max_length=18, null=False, blank=False)
    banco = models.CharField(max_length=45, null=True, blank=True)
    email = models.CharField(max_length=45, blank=True, null=True)
    is_favorite = models.BooleanField(default=False)
    person = models.ForeignKey(persona, on_delete=models.CASCADE, null=True, blank=True)
    alias = models.CharField(max_length=45, null=True)
    tipo_contacto = models.ForeignKey(tipo_transferencia, on_delete=models.DO_NOTHING, null=False, blank=True,
                                      default=3)
    rfc_beneficiario = models.CharField(max_length=13, null=True, blank=True)
    is_active =models.BooleanField(default=True)
    objects = ManagerContacts()

    class Meta:
        permissions = [('can_create_contact_v2', 'Puede crear contacto'),
                       ('can_edit_contact_v2', 'Puede editar contacto'),
                       ('can_get_contact_v2', 'Puede ver contacto')]


class grupo(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    nombreGrupo = models.CharField(max_length=45, null=False, blank=False)
    fechacreacion = models.DateTimeField(auto_now_add=True)
    fechamodificacion = models.DateTimeField(auto_now=True)


class grupoContacto(models.Model):
    group = models.ForeignKey(grupo, on_delete=models.CASCADE, related_name="group")
    contacts = models.ForeignKey(contactos, on_delete=models.CASCADE, related_name="contacts")
    objects = ManagerGroupContact()

class CatOperaciones (models.Model):   #operaciones que se pueden realizar con los contactos
    id = models.AutoField(primary_key=True, editable=False)
    accion = models.CharField(max_length=7)
    descripcion = models.TextField(max_length=50)

class HistoricoContactos(models.Model):   #bitacora de movimientos con contactos
    id = models.AutoField(primary_key=True, editable=False)
    usuario = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    datos = models.TextField(max_length=150)
    fechaRegistro = models.DateTimeField(auto_now_add=True)
    operacion = models.ForeignKey(CatOperaciones, on_delete=models.DO_NOTHING)
    contactoRel = models.ForeignKey(contactos, on_delete=models.DO_NOTHING)
