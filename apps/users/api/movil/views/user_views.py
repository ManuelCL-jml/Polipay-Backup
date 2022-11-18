from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView

from apps.users.management import get_information_client, get_Object_orList_error, createCodeCache
from apps.users.api.movil.serializers.account_serializer import serializerCuentaWalletIn
from apps.users.api.movil.serializers.user_serializer import *
from apps.users.views import GeneralLoginGenericViewSet
from apps.users.messages import createMessageWelcome
from apps.users.models import tarjeta, persona
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog


from polipaynewConfig.inntec import change_status


class createUserAcountMovil(viewsets.GenericViewSet):
	serializer_class = serializerUserWalletIn
	serializer_acc = serializerCuentaWalletIn
	#permission_classes = [IsAuthenticated]
	permission_classes = ()

	def create(self, request):
		# (mar 18.01.2022 07:27am - ChrAvaBus) Se agrega linea temporal para no permitir el registro
		# 	desde las apps, por incidentes con usuarios de Adelante Zapopan.
		return Response({"status": "Por el momento no se permiten registros."}, status=status.HTTP_200_OK)
		"""
		serializer = self.serializer_class(data=request.data, context={'ip': get_information_client(request)})

		if serializer.is_valid(raise_exception=True):
			instancePerson = serializer.save()
			serializerAccount = self.serializer_acc(data=request.data)
			if serializerAccount.is_valid(raise_exception=True):
				serializerAccount.save(instancePerson)
				createMessageWelcome(instancePerson, request.data['password'])
				msg = LanguageUnregisteredUser(request.data["lang"], "Reg007BE")
				#return Response({"status": "Tu cuenta fue creada\ncorrectamente."}, status=status.HTTP_200_OK)
				return Response({"status": msg}, status=status.HTTP_200_OK)
		"""

	def put(self, request):
		letter = ''
		userInstance = get_object_or_404(persona, email=request.data['email'])
		cuentaInstance = get_Object_orList_error(tarjeta, id=request.data['id'])
		if request.data['status']:
			reponse = change_status(cuentaInstance.TarjetaId, '00', 'Activada ' )
			cuentaInstance.status = "00"
		else:
			reponse = change_status(cuentaInstance.TarjetaId, '28', 'Bloqueada ' )
			cuentaInstance.status = "28"
		cuentaInstance.is_active = request.data['status']
		cuentaInstance.save()
		msg	= reponse[0]['Mensaje']
		if reponse[1] == 200:
			msg = LanguageRegisteredUser(userInstance.id, "Reg008BE")
		#return Response({"status": reponse[0]['Mensaje']}, status=status.HTTP_200_OK)
		return Response({"status": msg}, status=status.HTTP_200_OK)

	def delete(self, request):
		user = get_object_or_404(persona, email=request.data['email'])
		user.state = False
		user.is_active = False
		user.save()

		msg = LanguageUnregisteredUser(request.data["lang"], "Reg009BE")
		#return Response({'status': 'Cuenta eliminada satisfactoriamente'}, status=status.HTTP_200_OK)
		return Response({'status': msg}, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------------------------------

class LoginMovil(GeneralLoginGenericViewSet):
	serializer_class = serializerLoginIn
	serializer_class_out = serializerUserOut
	#permission_classes = [IsAuthenticated]
	permission_classes = ()


# --------------------------------------------------------------------------------------------------

class ChangePassword(viewsets.GenericViewSet):
	serializer_class = serializerChangePassIn
	#permission_classes = [IsAuthenticated]
	permission_classes = ()

	def get_persona(self, instance, request):
		return get_Object_orList_error(instance, email=request.data['email'])

	def create(self, request):
		RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance = persona.objects.filter(email=request.data['email']).exists()
		if not queryExistValOfInstance:
			msg = LanguageUnregisteredUser(request.data["lang"], "BackEnd001")
			r = {"status": msg}
			RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		instance = self.get_persona(persona, request)
		createCodeCache(instance)
		msg = LanguageUnregisteredUser(request.data["lang"], "Log005")
		r = {"status": msg}
		RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(request), objJsonResponse=r)
		#return Response({"status": "Hemos enviado a su email un codigo de verificación"}, status=status.HTTP_200_OK)
		return Response(r, status=status.HTTP_200_OK)

	def put(self, request):

		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance = persona.objects.filter(email=request.data['email']).exists()
		if not queryExistValOfInstance:
			msg = LanguageUnregisteredUser(request.data["lang"], "BackEnd001")
			r = {"status": msg}
			RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		instance = self.get_persona(persona, request)
		serializer = self.serializer_class(data=request.data, context={"idUser":-1, "url":get_info(request)})
		serializer.is_valid(raise_exception=True)
		serializer.save(instance)
		msg = LanguageUnregisteredUser(request.data["lang"], "Log003")
		r = {"status": msg}
		RegisterSystemLog(idPersona=-1, type=1, endpoint=get_info(request), objJsonResponse=r)
		#return Response({"status": "Tu contraseña ha sido\nguardada correctamente."}, status=status.HTTP_200_OK)
		return Response(r, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------------------------------

class UpdateUser(viewsets.GenericViewSet):
	serializer_class	= serializerUpdateUser
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		pass

	def put(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		instance = get_Object_orList_error(persona, pk=request.data['id'])
		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		serializer.is_valid(raise_exception=True)
		serializer.update(instance, serializer.validated_data)
		msg = LanguageRegisteredUser(request.data["id"], "Das008")
		r = {"status": msg}
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
		return Response(r, status=status.HTTP_200_OK)
		#return Response({"status": "Tus datos se actualizaron\ncorrectamente."}, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------------------------------

class ChangePaswordOld(GenericAPIView):
	serializer_class	= serializerEditPasswordIn
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self):
		return

	def put(self, request, pk):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		request.data["id"]	= pk
		instance = get_Object_orList_error(persona, id=pk)
		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		serializer.is_valid(raise_exception=True)
		serializer.update(instance, serializer.validated_data)
		msg = LanguageRegisteredUser(pk, "Das002")
		r = {"status": msg}
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
		#return Response({"status": "Tu contraseña se\nactualizó correctamente."}, status=status.HTTP_200_OK)
		return Response(r, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------------------------------


class EditarToken(viewsets.GenericViewSet):
	permission_classes = ()
	serializer_class = serializerEditTokenIn

	def create(self):
		return

	def put(self, request):
		pk = self.request.query_params["id"]
		instance = get_Object_orList_error(persona, id=pk)
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			serializer.update(instance, serializer.validated_data)
			return Response({"status": "token actualizado"}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------------------------
class Upload_photo(viewsets.GenericViewSet):
	serializer_class = SerializerEditPhoto
	permission_classes = [IsAuthenticated]
	#permission_classes = ()

	def create(self):
		return

	def put(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		pk_user = self.request.query_params["id"]
		instance = get_Object_orList_error(persona, id=pk_user)
		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			photo = serializer.Update_image(instance)
			r = {"status": photo}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			#msg = LanguageRegisteredUser(pk_user, "Das005")
			#return Response({"status": msg, "url":photo}, status=status.HTTP_200_OK)
			return Response(r, status=status.HTTP_200_OK)

	def delete(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		pk_user = self.request.query_params["id"]
		instance = get_Object_orList_error(persona, id=pk_user)
		instance.photo.delete()
		msg = LanguageRegisteredUser(pk_user, "Das006")
		r = {"status": msg}
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
		return Response(r, status=status.HTTP_200_OK)
		#return Response({"status": "Foto eliminada"}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------------------------

class ActualizarCount(viewsets.GenericViewSet):
	serializer_class = ChangeDeviceSerializerIn
	permission_classes = ()

	def list(self, request):
		instance = get_Object_orList_error(persona, id=self.request.query_params['id'])
		serialzierCount = serializerUserOut(instance)
		return Response(serialzierCount.data, status=status.HTTP_200_OK)


class ChangeNip(viewsets.GenericViewSet):
	serializer_class	= serializerChangeNip
	queryset			= persona.objects.all()
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			serializer.changeNip()
			msg = LanguageRegisteredUser(self.request.user.id, "Das010")
			r	= {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)
			#return Response({"status": "NIP guardado con éxito"}, status=status.HTTP_200_OK)

# ---------------------------------------------------------------------------------------------

class UpdateToken(viewsets.GenericViewSet):
	serializer_class	= SerializerUpdateToken
	queryset			= persona.objects.all()
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()

	def create(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			serializer.updateToken(data=request.data)
			"""
			result	= {
				"code":[200],
				"status":"OK",
				"detail":[
					{
						"field":"token",
						"data":"****",
						"message":"Se actualizó correctamente\nTu Token Físico."
					}
				]	
			}
			return Response(result, status=status.HTTP_200_OK)
			"""
			msg = LanguageRegisteredUser(request.data["id"], "Das007")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)
			#return Response({"status": "Se actualizó correctamente\nTu Token de Seguridad."}, status=status.HTTP_200_OK)

# ---------------------------------------------------------------------------------------------



# -------- (ChrAvaBus Vie23.12.2021) v3 --------

class UpdateLanguage(UpdateAPIView):
	serializer_class = SerializerUpdateLanguage
	#permission_classes = ()
	permission_classes = [IsAuthenticated]

	def update(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)
		pk  				= self.request.query_params["id"]
		request.data["id"]  = pk

		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			serializer.updateLanguage(serializer.validated_data)
			r = {"status": "Idioma actualizado correctamente."}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)


class DeleteCard(DestroyAPIView):
	serializer_class	= SerializerDeleteCard
	permission_classes	= [IsAuthenticated]
	#permission_classes = ()


	def destroy(self, request):
		RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonRequest=self.request.data)

		pk 			= request.data["persona"]
		card		= request.data["tarjeta"]
		nameCard	= request.data["alias"]

		# Validación para parametrizar mensaje en get_Object_orList_error
		queryExistValOfInstance = tarjeta.objects.filter(id=request.data["idCard"]).exists()
		if not queryExistValOfInstance:
			msg = LanguageRegisteredUser(self.request.user.id, "BackEnd001")
			r = {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_400_BAD_REQUEST)

		serializer = self.serializer_class(data=request.data, context={"idUser":self.request.user.id, "url":get_info(request)})
		if serializer.is_valid(raise_exception=True):
			serializer.deleteCard(serializer.validated_data)
			msg = LanguageRegisteredUser(pk, "BackEnd004")
			msg	= msg.replace("<card>", nameCard)
			r	= {"status": msg}
			RegisterSystemLog(idPersona=self.request.user.id, type=1, endpoint=get_info(request), objJsonResponse=r)
			return Response(r, status=status.HTTP_200_OK)


