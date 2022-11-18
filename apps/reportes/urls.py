#  Modulos nativos
from rest_framework.routers import SimpleRouter

# Modulos locales
from .views import ReporteViewSet


router = SimpleRouter()
router.register(r'v2/tarjeta', ReporteViewSet, basename='reportar-tarjeta'),

urlpatterns = router.urls
