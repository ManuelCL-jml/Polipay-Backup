from django.db import models


class log(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    url = models.TextField(max_length=255)
    persona = models.ForeignKey("users.persona", on_delete=models.DO_NOTHING)
    json_content = models.TextField(max_length=255)
    response = models.TextField(max_length=255)
