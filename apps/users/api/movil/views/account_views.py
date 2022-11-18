from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status

from apps.users.api.movil.serializers.account_serializer import serializerCuentaWalletIn, serializerAcountIn, \
	serializerCuentaWalletTajetaIn, serializerEditAlias
from apps.users.api.movil.serializers.user_serializer import serializerUserOut
from apps.users.management import get_Object_orList_error, getTotalsCounts
from apps.users.models import persona, cuenta, tarjeta
from polipaynewConfig.inntec import *
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.Users.get_id import get_id
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog


# ----------------------------------------------------------------------------------------------------

class createAccount(viewsets.GenericViewSet):
	serializer_class = serializerCuentaWalletTajetaIn
	queryset = cuenta.objects.all()
	permission_classes = [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		instancePerson = get_Object_orList_error(persona, email=request.data['email'])
		acount = cuenta.objects.get(persona_cuenta_id=instancePerson.id)
		tarjetas = tarjeta.objects.filter(cuenta_id=acount.id)
		count = getTotalsCounts(tarjetas)
		if count == False:
			idPersona	= get_id(campo="email", valorStr=str(request.data["email"]))
			msg			= LanguageRegisteredUser(idPersona, "Das007BE")
			return Response({"status": msg}, status.HTTP_400_BAD_REQUEST)
			#return Response({"status": "número de cuentas exedidas, solo 5 cuentas"}, status.HTTP_400_BAD_REQUEST)

		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			serializer.save(acount)
			serializerUser = serializerUserOut(instancePerson)
			idPersona	= get_id(campo="email", valorStr=str(request.data["email"]))
			msg			= LanguageRegisteredUser(idPersona, "Das003")
			return Response({"status": msg, "data": serializerUser.data}, status=status.HTTP_201_CREATED)
			#return Response({"status": "cuenta creada", "data": serializerUser.data}, status=status.HTTP_201_CREATED)


class actualizeAcuounts(viewsets.GenericViewSet):
	serializer_class = serializerCuentaWalletIn
	queryset = cuenta.objects.all()
	permission_classes = ()

	def list(self, request):
		acounts = get_Counts()
		accounts = []
		for acount in acounts:
			serializer = serializerAcountIn(acount)
			data = serializer.save(serializer.data)
			if data:
				accounts.append({"card": data})
		return Response({"cards": accounts},status=status.HTTP_200_OK)


class changeNip(viewsets.GenericViewSet):
	serializer_class = serializerCuentaWalletIn
	queryset = cuenta.objects.all()
	permission_classes = ()
	def create(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		response, statusResponse = change_nip(request.data['tarjeta'], request.data['nip'], request.data['fechexp'])
		if str(statusResponse) == '400':
			r = {"status": [response['Message']]}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)
		else:
			r = {"status": [response['Message']]}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)

#class solicitudTarjetas(viewsets.GenericViewSet):
#    serializer_class = serializerCuentaWalletIn
#    queryset = tarjeta.objects.all
#    permission_classes = ()

 #   def create(self, request):
  #      response = solicitud_tarjetas(request.data['cliente'], request.data['producto'], request.data['cantidad'], request.data['puntoE'],
   #                                   request.data['datoP1'], request.data['datoP2'], request.data['correo'])

class editAliasCard(viewsets.GenericViewSet):
	serializer_class = serializerEditAlias
	queryset = tarjeta.objects.all()
	permission_classes = [IsAuthenticated]
	#permission_classes = ()

	def create(self):
		pass

	def put(self,request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		pk_card = self.request.query_params["id"]
		if pk_card:
			instance = get_Object_orList_error(tarjeta,id=pk_card)
			serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
			if serializer.is_valid(raise_exception=True):
				serializer.alias_rename(instance)
				serializer.cvc_rename(instance)
				serializer.fechaexp_rename(instance)
				idPersona	= get_id(campo="card", valorStr=str(pk_card))
				msg			= LanguageRegisteredUser(idPersona, "Das004")
				r = {"status": msg}
				RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
				return Response(r, status=status.HTTP_200_OK)
				#return Response({"status":"Datos de tarjeta actualizados"},status=status.HTTP_200_OK)
		else:
			idPersona	= get_id(campo="card", valorStr=str(pk_card))
			msg			= LanguageRegisteredUser(idPersona, "Das008BE")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r,status=status.HTTP_400_BAD_REQUEST)
			#return Response({"status": "Se esperaba una id de tarjeta"}, status=status.HTTP_400_BAD_REQUEST)
