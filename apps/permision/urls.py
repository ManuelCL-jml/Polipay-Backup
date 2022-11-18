# Modulos nativos
from rest_framework import routers

# Modulos locales
from .views import *
from . import views

router = routers.SimpleRouter()
# end points news
router.register(r'v2/list/permission', listPremision, basename='createStatus')
router.register(r'v2/create/group', createGroup, basename='createGroup')
router.register(r'v2/add/permissions/group', addPermisionssGroups, basename='addPermisionssGroups')
router.register(r'v2/add/user/group', addUSerGruop, basename='addPermisionssGroups')
router.register(r'v2/remove/permissions/group', removePermisionssGroups, basename='removePermisionssGroups')
router.register(r'v2/remove/user/group', removeUSerGroup, basename='removeUSerGroup')
router.register(r'v2/delete/group', deleteUSerGroup, basename='deleteUSerGroup')
## JAMH
router.register(r'v3/Permisos/list', ListarPermisos, basename='listar-permisos')
router.register(r'v3/PerGru/list',  ListarGrupoPermisos, basename='listar-permisosGrupos')
router.register(r'v3/PerGruNom/list', ListarGruposDePermisoNombre, basename='listar-permisosGrupos')
router.register(r'v3/Grupo/create', CrearNombreGrupoPermisos, basename='listar-permisosGrupos')
router.register(r'v3/Grupo/delete', EliminarGrupoPermisos, basename='listar-permisosGrupos')
router.register(r'v3/PerGru/cu', GrupoPermisos, basename='listar-permisosGrupos')
router.register(r'v3/UserGru/update', editarGrupoPermisoUser, basename='listar-permisosGrupos')
#Pruebas
router.register(r'v3/permisoprueba1', ListarGruposDePermisoNombrePrueba, basename='listar-permisosGrupos')

urlpatterns = router.urls
