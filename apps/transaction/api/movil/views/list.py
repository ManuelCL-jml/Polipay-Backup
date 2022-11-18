from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status

from apps.transaction.management import *
from apps.users.models import *
from apps.transaction.models import *
from apps.transaction.api.movil.serializers.list import *
from apps.transaction.api.movil.serializers.createTransaction import *


class listTypes(viewsets.GenericViewSet):
	serializer_class	= ()
	queryset			= ()
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def list(self, request):
		type = self.request.query_params['type']

		if type == 'tipotrans':
			query = tipo_transferencia.objects.all()
			serializer = serializerTipoTransferenciaOut(query, many=True)
		if type == 'Status':
			query = Status.objects.all()
			serializer = serializerStatusOut(query, many=True)
		if type == 'bancos': 
			is_third = self.request.query_params['isThird']
			if is_third == '0':
				query = bancos.objects.all()
			if is_third == '1':
				query = bancos.objects.all().exclude(id=86)	
			serializer = serializerBancosOut(query, many=True)

		return Response(serializer.data, status=status.HTTP_200_OK)


