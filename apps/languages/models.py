from django.db import models
from apps.users.models import persona


class Cat_languages(models.Model):
    # Catalogo de lenguajes
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=30)
    code_name =models.CharField(max_length=8)
    description = models.CharField(max_length=255)
    json_content = models.TextField(max_length=255)
    creation_date = models.DateTimeField(auto_now_add=True)

class Language_Person(models.Model):
    # lenguajes de personas
    id = models.AutoField(primary_key=True, editable=False)
    person = models.ForeignKey(persona, on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)
    selected_language = models.ForeignKey(Cat_languages, on_delete=models.DO_NOTHING, default=1)