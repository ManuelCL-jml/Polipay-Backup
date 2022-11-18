from django.utils import timezone
from django.db import models
# from users.models import persona, cuenta


class producto(models.Model):
    # tablas para la definicion de productos
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=30, null=False, blank=False)
    descripcion = models.CharField(max_length=250, null=False, blank=False)


class rel_user_prod(models.Model): #eliminar ??? ya existe relacion con cuenta -producto
    # tabla para relacionar productos y usuarios
    id = models.AutoField(primary_key=True, editable=False)
    cliente = models.ForeignKey("users.persona", on_delete=models.DO_NOTHING)
    product = models.ForeignKey(producto, on_delete=models.CASCADE)
    # cuenta_rel = models.ForeignKey(cuenta, on_delete=models.DO_NOTHING, default=1)


class servicios(models.Model):
    # tabla para definicion de servicios
    id = models.AutoField(primary_key=True, editable=False)
    nombre = models.CharField(max_length=30, null=False, blank=False)
    descripcion = models.CharField(max_length=250, null=False, blank=False)


class rel_prod_serv(models.Model):
    # tabla para relacionar productos y sus distintos servicios
    id = models.AutoField(primary_key=True, editable=False)
    product = models.ForeignKey(producto, on_delete=models.DO_NOTHING)
    service = models.ForeignKey(servicios, on_delete=models.DO_NOTHING)


class freq_cobro(models.Model):
    # tabla para definir los distintos tipos de frecuencia de cobro
    id = models.AutoField(primary_key=True, editable=False)
    frecuencia = models.CharField(max_length=30, null=False, blank=False)
    descripcion = models.CharField(max_length=250, null=False, blank=False)

# class caracteristicas(models.Model): #eliminar ya existe tabla especifica para comisiones
#     # tabla para guardar comisiones correspondientes
#     tipo_Monto = (('%', 'Porcentaje'), ('$', 'cantidad'))
#
#     id = models.AutoField(primary_key=True, editable=False)
#     nombre = models.CharField(max_length=30, null=False, blank=False)
#     descripcion = models.CharField(max_length=250, null=False, blank=False)
#     comision = models.BooleanField(default=True)                                    #indica si la comision es positiva o negativa
#     monto = models.FloatField(null=False, blank=False)                          # monto de la comision
#     t_monto = models.CharField(max_length=1, choices=tipo_Monto, default='$')
#     cobro = models.ForeignKey(freq_cobro, on_delete= models.DO_NOTHING)
#     f_persona = models.ForeignKey("users.persona", on_delete=models.DO_NOTHING,
#                                   default=94,
#                                   related_name="Caracteristica_cliente")
#     fecha_registro = models.DateTimeField(auto_now_add=True)
#     fecha_autorizacion = models.DateTimeField(null=True, blank=True)
#     usuario_autorizacion = models.ForeignKey("users.persona", on_delete=models.DO_NOTHING,
#                                              default=94,
#                                              related_name="admin_autoriza")
#
# class rel_serv_cara(models.Model):# eliminar
#     # tabla para relacionar comisiones y/o caracteristicas con servicios
#     id = models.AutoField(primary_key=True, editable=False)
#     service = models.ForeignKey(servicios, on_delete=models.DO_NOTHING)
#     comisiones = models.ForeignKey(caracteristicas, on_delete=models.DO_NOTHING)