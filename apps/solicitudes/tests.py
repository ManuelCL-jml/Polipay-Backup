from django.test import TestCase
from polipaynewConfig.wsgi import *
from apps.solicitudes.models import *
from apps.users.management import filter_all_data_or_return_none, filter_data_or_return_none

# p = TipoSolicitud.objects.create(nombreSol='Apertura', descripcionSol='Apertura de un centro de costos, cliente externo o colaborador')
# p = TipoSolicitud.objects.create(nombreSol='Cierre', descripcionSol='Apertura de un centro de costos, cliente externo o colaborador')
# p = TipoSolicitud.objects.create(nombreSol='Cambio Representante', descripcionSol='Cambio de un representante legal')
# p = TipoSolicitud.objects.create(nombreSol='Cambio Domicilio Fiscal', descripcionSol='Cambio de un domicilio fiscal')
# p = TipoSolicitud.objects.create(nombreSol='Cambio Clabe Destino Final', descripcionSol='Cambio de clabe destino')

#
# p = EdoSolicitud.objects.create(nombreEdo='Pendiente')
# p = EdoSolicitud.objects.create(nombreEdo='Devuelta')
# p = EdoSolicitud.objects.create(nombreEdo='Actualizacion')
# p = EdoSolicitud.objects.create(nombreEdo='Autorizada')
#
# # d = filter_all_data_or_return_none(Solicitudes, personaSolicitud_id=482)
# d = Solicitudes.objects.all().filter(tipoSolicitud_id=1)
#
# for i in d:
#     print(i.tipoSolicitud.nombreSol)
#     print(i.id)


d = Solicitudes.objects.all().values('id', 'nombre', 'fechaSolicitud', 'intentos', 'estado_id', 'personaSolicitud_id',
                                     'tipoSolicitud_id', 'dato_json')

for i in d:
    print(i)
