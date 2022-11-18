# Modulos nativos
from rest_framework import serializers

# Modulos locales
from .models import Reporte
from .choices import TYPE_REPORT_CHOICE
from apps.users.models import persona
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser

class ReporteSerializer(serializers.ModelSerializer):
    type_report = serializers.ChoiceField(choices=TYPE_REPORT_CHOICE)
    description = serializers.CharField()
    # persona     = serializers.IntegerField()

    #def validate_persona(self, value):
    #    queryExistePersona  = persona.objects.filter(id=value).exists()
    #    if not queryExistePersona:
    #        msg = LanguageRegisteredUser(self.initial_data.get("persona"), "Das012BE")
    #        raise serializers.ValidationError({"status": msg})
    #    return value

    class Meta:
        model = Reporte
        fields = ['type_report', 'description']
