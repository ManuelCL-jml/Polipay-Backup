from rest_framework import serializers
from .....notifications.models import general_advise


class SerializerGeneralNotificationsOut(serializers.Serializer):
    id = serializers.IntegerField()
    #active = serializers.BooleanField()
    #tittle = serializers.CharField()
    #message = serializers.CharField()
    creation_date = serializers.DateTimeField()
    data = serializers.SerializerMethodField()

    def get_data(self, obj):
        info = {
            "showAlert" : obj.active,
            "title" : obj.tittle,
            "message" : obj.message,
            "showBtnLogin" : obj.btn_login,
        }
        return info

