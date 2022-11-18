from dataclasses import dataclass
from typing import Dict, List

from polipaynewConfig.wsgi import *
from apps.transaction.models import bancos


@dataclass
class ConstantsTransaction:

    # (ChrGil 2021-11-23) Regresa un diccionario de todos los bancos existentes
    @property
    def all_bancks(self) -> Dict:
        return dict(bancos.objects.all().values_list('participante', 'id'))

    # (ChrGil 2021-11-21) Lista de tipo de transferencias en la bd, unicamenta se utiliza para transacciones masivas
    def get_list_tipo_transferencia_id(self) -> List:
        return [1, 2]
