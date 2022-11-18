from django.db import models

from apps.suppliers.manager import ManagerCatProductsParams, ManagerCatSupplier


class cat_type(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=50, unique=True)


class cat_supplier(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    type = models.ForeignKey(cat_type, on_delete=models.DO_NOTHING, related_name="tipo_proveedor")
    name_short = models.CharField(max_length=5, unique=True)
    name_large = models.CharField(max_length=25, unique=True)
    description = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    objects = ManagerCatSupplier()


class cat_products_params(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    supplier = models.ForeignKey(cat_supplier, on_delete=models.DO_NOTHING, related_name="proveedor_relacionado")
    json_content = models.TextField(max_length=None)
    objects = ManagerCatProductsParams()
