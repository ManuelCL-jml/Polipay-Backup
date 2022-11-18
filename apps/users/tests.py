from apps.contacts.models import contactos
from polipaynewConfig.wsgi import *
from apps.users.models import cuenta

# Crear super usuario
# p = persona.objects.create_admin(
#     email="america.monsalvo@polimentes.com",
#     name="America Berenice",
#     last_name="Mansalvo Flores",
#     phone="+52636363644",
#     is_superuser=True,
#     is_staff=True,
#     fecha_nacimiento="1998-09-09",
#     ip_address="127.0.0.0",
#     a_paterno="",
#     a_materno="",
#     password="Amereica123",
# )


# SAL      ---> Saldos
# DIS       ---> Dispersion
# TRA      ---> Transferencia
# REC      ----> Recibidas
# REF + SAL + AAAAMMDDHHMMSS + XXXX
# REFDIS202110221035695555

