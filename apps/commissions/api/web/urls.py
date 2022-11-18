from django.urls import path

from apps.commissions.api.web.views.views_commision_debt import PayComissionPositiveDebts
from apps.commissions.api.web.views.views_commision_pay import PayComissionPositive
from apps.commissions.api.web.views.views_list_comissions import ListComissionPositive, DetailComissionPositive
from apps.commissions.api.web.views.views_list_comissions import ListComissionPositive, DetailComissionPositive, \
    DetailComissionCompany, UpdateComission

urlpatterns = [
    path('v3/LisComPos/list/', ListComissionPositive.as_view()),
    path('v3/DetComPos/get/', DetailComissionPositive.as_view()),
    path('v3/PayComPos/get/', PayComissionPositive.as_view()),
    path('v3/PayComPosDeb/get/', PayComissionPositiveDebts.as_view()),
    path('v3/DetComCom/get/', DetailComissionCompany.as_view()),
    path('v3/UpdCom/update/', UpdateComission.as_view()),
]
