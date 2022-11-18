# Modulos nativos
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status

# Modulos locales
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog
from MANAGEMENT.EndPoint.EndPointInfo import get_info

from .serializers import ReporteSerializer
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser

class ReporteViewSet(GenericViewSet):
    serializer_class = ReporteSerializer
    permission_classes = [IsAuthenticated]
    #permission_classes = ()

    def create(self, request):
        serializer = self.serializer_class(data=request.data)

        log_dict = {
            "params": request.query_params,
            "body": request.data
        }

        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=log_dict)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        msg = LanguageRegisteredUser(self.request.user.id, "Das001")
        R   = {"status":msg}
        #R = {'detail': 'Tu reporte se envió satisfactoriamente.\n\nContáctate con un asesor Polipay al número (+52) 556 827 8522 o (+52) 554 170 4129 para seguir el proceso de reposición.'}
        RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request),
                          objJsonRequest=R)
        return Response(R, status=status.HTTP_200_OK)


