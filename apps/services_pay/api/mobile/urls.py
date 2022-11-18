from django.urls import path
from rest_framework import routers
from .views.transmitter_view import *
from .views.category_view import *


routers = routers.SimpleRouter()

routers.register(r'v2/transmitter/crud', TransmitterCrud, basename='Transmitter-crud')
routers.register(r'v2/refrence/crud', ReferenceCrud, basename='Reference-crud')
routers.register(r'v2/transmitterhaverefrence/crud', TransmitterHaveReferenceCrud, basename='TransmitterHavReference-crud')
routers.register(r'v2/payservice', PayTransmitterCreate, basename='endpointPayTransmitterCreate')
routers.register(r'v2/category/crud', CategoryCrud, basename='endPointCrudCategory')
routers.register(r'v2/category/reference', CategoryCreateReference, basename='endPointCategoryReference')
routers.register(r'v2/frequenttransmitter/rd', FrequentTransmitterRD, basename='endpointFrequentTransmitterRD')
routers.register(r'v2/checkbalanceRE/read', CheckBalanceRedEfectiva, basename='endpointCheckBalanceRedEfectiva')
routers.register(r'v2/checkcommissionRE/read', CheckCommissionRedEfectiva, basename='endpointCheckCommissionRedEfectiva')

urlpatterns = [] + routers.urls
