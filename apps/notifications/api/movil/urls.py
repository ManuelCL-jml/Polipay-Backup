from django.urls import path

from rest_framework import routers

from .views.notifications_view import *
from .views.general_notifications_view import ViewSetGeneralNotifications

router = routers.SimpleRouter()

router.register(r'v3/Notification/list', ListNotification, basename='listadoDeNoitificaciones')
router.register(r'v3/Notification/active', ActiveNotification, basename='numeroDeNoitificacionesActivas')
router.register(r'v3/Notification/general_notifications', ViewSetGeneralNotifications, basename='generalNotifications')


#urlpatterns = router.urls

urlpatterns = [
                  path('v3/Notification/update',  UpdateNotification.as_view()),
] + router.urls
