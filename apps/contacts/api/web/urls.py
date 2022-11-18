from django.urls import path

from rest_framework import routers

from apps.contacts.api.web.views.contacts_views import CreateFrecuentContacts, MakeOrBreakFrecuentContact, \
    DeleteFrecuentContact, ListFrecuentsContacts, UpdateFrecuentContact, ReactivateFrecuentContact, \
    DetailFrecuentContact, ListFrecuentContactsCostCenters, ListFrecuentContactsPolipayToThirPerson
from apps.contacts.api.web.views.contacts_groups_views import CreateContactsGroups, UpdateContactsGroups, DeleteContactsGroups, ListFrecuentsContactsGroups, DetailsFrecuentsContactsGroups


router = routers.SimpleRouter()

# router.register(r'v2/contacts', contacto, basename='contactos')
# router.register(r'v2/grupo', grupos, basename='grupo')
# router.register(r'v2/grupo-contacto', grupoContactos, basename='grupoContacto')
# router.register(r'v2/persona', personaGrupoContacto, basename='grupoContactoPersona')
router.register(r'v2/FreCon/create', CreateFrecuentContacts, basename='prueba_de_token')
router.register(r'v2/FreCon/update', UpdateFrecuentContact, basename='prueba_de_token')
router.register(r'v2/FreConFav/update', MakeOrBreakFrecuentContact, basename='prueba_de_token')
router.register(r'v2/DelFreCon/delete', DeleteFrecuentContact, basename='prueba_de_token')
router.register(r'v2/ReaFreCon/update', ReactivateFrecuentContact, basename='prueba_de_token')
router.register(r'v2/GroFreCon/create', CreateContactsGroups, basename='prueba_de_token')
router.register(r'v2/PutGroFreCon/update', UpdateContactsGroups, basename='prueba_de_token')
# router.register(r'v2/DelGroFreCon/delete', DeleteContactsGroups, basename='prueba_de_token')

urlpatterns = [
    path('v2/LisFreCon/list/', ListFrecuentsContacts.as_view()),
    path('v2/LisFreConCosCen/list/', ListFrecuentContactsCostCenters.as_view()),
    path('v2/LisFreConPolToThiPer/list/', ListFrecuentContactsPolipayToThirPerson.as_view()),
    path('v2/DetFreCon/get/', DetailFrecuentContact.as_view()),
    path('v2/DelGroFreCon/delete/', DeleteContactsGroups.as_view()),
    path('v2/LisGroFreCon/list/', ListFrecuentsContactsGroups.as_view()),
    path('v2/DetGroFreCon/get/', DetailsFrecuentsContactsGroups.as_view()),#nuevo
] + router.urls
