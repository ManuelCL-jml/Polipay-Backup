from rest_framework import serializers

from apps.notifications.models import notification
from apps.users.models import persona
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser


class SerializerCreateNotification(serializers.Serializer):
    id  = serializers.IntegerField(required=True, allow_null=False)
    person  = serializers.IntegerField(required=True, allow_null=False)
    is_active   = serializers.BooleanField(default=True)
    deactivation_date   = serializers.DateTimeField(required=True, allow_null=False)

    def validate_id(self, value):
        queryExisteNotificacion = notification.objects.filter(id=value).exists()
        if not queryExisteNotificacion:
            msg = LanguageRegisteredUser(self.initial_data.get("person"), "Not003BE")
            raise serializers.ValidationError({"status": msg})
            #raise serializers.ValidationError({"status": "Notificación no existe"})
        return value

    def validate_person(self, value):
        queryExistePersona  = persona.objects.filter(id=value).exists()
        if not queryExistePersona:
            msg = LanguageRegisteredUser(self.initial_data.get("person"), "Not004BE")
            raise serializers.ValidationError({"status": msg})
            #raise serializers.ValidationError({"status": "Persona no existe"})
        return value

    def validate_is_active(self, value):
        if value == None or value == "":
            msg = LanguageRegisteredUser(self.initial_data.get("person"), "Not005BE")
            raise serializers.ValidationError({"status": msg})
            #return serializers.ValidationError({"status":"Valor incorrecto para is_active"})
        else:
            return value

    def validate_deactivation_date(self, value):
        if value == None or value == "":
            msg = LanguageRegisteredUser(self.initial_data.get("person"), "Not006BE")
            raise serializers.ValidationError({"status": msg})
            #return serializers.ValidationError({"status": "Valor incorrecto para fecha"})
        else:
            return value

    def createNotification(self, ):
        pass

    def updateNotification(self, validated_data, instance):
        instance.is_active  = validated_data.get("is_active", instance.is_active)
        instance.deactivation_date  = validated_data.get("deactivation_date", instance.deactivation_date)
        instance.save()
        return instance
