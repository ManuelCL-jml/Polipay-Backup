from django.urls import path

from rest_framework import routers

from .views.user_views import *
from .views.account_views import *
from ..web.views.user_views import ListUser, EditAccountsUser

router = routers.SimpleRouter()
router.register(r'v2/login/user', LoginMovil, basename='LoginMovil')
router.register(r'v2/create/user/account', createUserAcountMovil, basename='createUserAcountMovil')
router.register(r'v2/forgot/password', ChangePassword, basename='ChangePassword')
router.register(r'v2/create/account', createAccount, basename='createAccount')
router.register(r'v2/update/alias', editAliasCard, basename='UpdateAlias')
router.register(r'v2/upload/image', Upload_photo, basename='UpdatePhoto')
router.register(r'v2/Token/update', UpdateToken, basename='UpdateToken')
router.register(r'v2/update/user', UpdateUser, basename='UpdateUser')
router.register(r'v2/update/nip', ChangeNip, basename='ChangeNip')

router.register(r'v2/get/counts', actualizeAcuounts, basename='actualizeAcuounts')
router.register(r'v2/change/nip', changeNip, basename='changeNip')
router.register(r'v2/list/users', ListUser, basename='list-users')
router.register(r'v2/list/accounts', EditAccountsUser, basename='list-accounts')

urlpatterns = [
    path('v2/change/password/<int:pk>', ChangePaswordOld.as_view(), name='change-password'),
    path('v3/Language/update', UpdateLanguage.as_view()),
    path('v3/Card/delete', DeleteCard.as_view()),
] + router.urls
