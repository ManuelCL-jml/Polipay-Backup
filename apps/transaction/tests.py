from apps.transaction.models import transferencia
from polipaynewConfig.wsgi import *


transactions = transferencia.objects.filter(cta_beneficiario="2995225120230653")
for transaccion in transactions:
    print(transaccion)


