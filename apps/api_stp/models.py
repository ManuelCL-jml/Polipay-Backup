from django.db import models
from apps.transaction.models import transferencia


class Cat_supplier(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)
    large_name = models.CharField(max_length=50)
    description = models.TextField(max_length=255)
    date_create = models.DateTimeField(auto_now_add=True)


class Supplier_transactions(models.Model):
    id = models.AutoField(primary_key=True)
    transfer = models.ForeignKey(transferencia, on_delete=models.DO_NOTHING)
    cat_supplier = models.ForeignKey(Cat_supplier, on_delete=models.DO_NOTHING)
    json_content = models.JSONField(max_length=255)
    date_create = models.DateTimeField(auto_now_add=True)
    consumption_date = models.DateTimeField(auto_now=False, auto_now_add=False)
