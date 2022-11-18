from MANAGEMENT.Standard.errors_responses import MyHttpError
from .....notifications.models import general_advise
from rest_framework import viewsets, status
from rest_framework.response import Response

from ..serializers.general_notifications_serializer import SerializerGeneralNotificationsOut


class ViewSetGeneralNotifications(viewsets.GenericViewSet):
    queryset = general_advise.objects.all()
    permission_classes = ()

    def list(self, request):
        queryset = general_advise.objects.order_by('-creation_date')
        serializer = SerializerGeneralNotificationsOut(queryset, many=True)
        if len(queryset) > 0:
            return Response(serializer.data[0], status=status.HTTP_200_OK)
        else:
            err = MyHttpError("No existen registros", str())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
