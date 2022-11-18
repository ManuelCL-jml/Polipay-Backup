from django.urls import path

from rest_framework import routers

from apps.users.api.movil.views.user_views import EditarToken, Upload_photo
from .views.Contacts_view import *
from .views.GroupContact_view import *
from .views.Group_view import *

router = routers.SimpleRouter()

router.register(r'v3/FrequentAccounts/list', ListFrequentAccounts, basename='listadoDeFrecuentes')
router.register(r'v3/FrequentAccounts/create', CreateFrequentAccounts, basename='createDeFrecuentes')

router.register(r'v2/contacts', contacto, basename='contactos')
router.register(r'v2/grupo', grupos, basename='grupo')
router.register(r'v2/grupo-contacto', grupoContactos, basename='grupoContacto')
router.register(r'v2/persona', personaGrupoContacto, basename='grupoContactoPersona')
# (ManCal 05/11/2021) Se debe mover a apps.users.movil
router.register(r'v2/token', EditarToken, basename='prueba_de_token')

urlpatterns = [
    path('v3/FrequentAccounts/destroy', DestroyFrequentAccounts.as_view()),
    path('v3/FrequentAccounts/update',  UpdateFrequentAccounts.as_view()),
] + router.urls  
