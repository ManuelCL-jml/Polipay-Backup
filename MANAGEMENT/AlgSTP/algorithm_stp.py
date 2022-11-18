from dataclasses import dataclass

# (ChrGil 2021-12-07) Se calcula el algoritmo STP de Banxico para hacer unica una clabe
from typing import ClassVar, List, NoReturn, Dict, Any

from apps.users.models import cuenta
from polipaynewConfig.settings import PREFIX_STP_BECPOLIMENTES


@dataclass
class VerificationAlgorithmClabe:
    clabe: str
    _ponderacion: ClassVar[List[int]] = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]

    @property
    def exceute(self) -> str:
        return self._algoritmo_digito_verificacion

    @property
    def _algoritmo_digito_verificacion(self) -> str:
        result_list = self._cuenta_multiply_ponderacion(self._to_int_values_cuenta(self.clabe), self._ponderacion)
        a = self._return_mod_result_all_list(result_list)

        b = 10 - a
        result = b % 10

        return f'{self.clabe}{result}'

    def _to_int_values_cuenta(self, clabe: str) -> List[int]:
        return [int(element) for element in clabe]

    def _cuenta_multiply_ponderacion(self, list_cuenta: List[int], ponderacion: List[int]) -> List[int]:
        return [list_cuenta[index] * ponderacion[index] for index in range(0, 17)]

    def _return_mod_result_all_list(self, result: List[int]) -> int:
        mod = [result[index] % 10 for index in range(0, 17)]
        n = 0

        for value in mod:
            n += value

        mod_result_with_mod = n % 10
        return mod_result_with_mod


# (ChrGil 2021-12-07) Suma de (1 en 1) el numero de cuentas creadas
@dataclass
class GenerateNewClabe:
    company_id: int
    _empresa_cuenta_clabe: ClassVar[str] = ""
    _cuenta_clabe_actual: ClassVar[int] = 0
    _verification_algorithm: ClassVar[VerificationAlgorithmClabe] = VerificationAlgorithmClabe

    @property
    def _get_cuenta(self) -> cuenta:
        return cuenta.objects.get_object_cuenta(self.company_id)

    @property
    def execute(self) -> str:
        self._empresa_cuenta_clabe = self._get_cuenta.get_cuentaclabe()
        self._cuenta_clabe_actual = self._get_last_cuenta_clave.muestra_numero_centro_costos
        new_clabe = self._verification_algorithm(self.rebuild_key).exceute
        self._validate_cuenta_clabe_actual()
        return new_clabe

    @property
    def rebuild_key(self) -> str:
        self._cuenta_clabe_actual += 1

        return self._empresa_cuenta_clabe.replace(
            self._get_cuenta.get_last_digits, "{:04d}".format(self._cuenta_clabe_actual))

    @property
    def _get_last_cuenta_clave(self) -> cuenta:
        return cuenta.objects.select_related().filter(
            cuentaclave__startswith=self._get_cuenta.get_account_stp
        ).order_by('-fecha_creacion').first()

    def _validate_cuenta_clabe_actual(self) -> None:
        if self._cuenta_clabe_actual > 9999:
            raise ValueError('Solo es posible generar 9999 cuentas clabe, con su cuenta actual')
        ...


# (ChrGil 2022-01-25) Genera un cuenta nueva cuenta clabe autoincrementable
class GenerateClabe:
    _jumps: ClassVar[List[int]] = [2, 5, 9, 12, 16]
    _list_section_clabe: ClassVar[List[str]]
    clabe: ClassVar[str]

    def __init__(self, clabe: str):
        self._list_section_clabe = []
        self._split_cuenta_clabe([i for i in clabe])
        self._increase_number()

    # (ChrGil 2022-01-25) Hace un split de manera recursiva a la clabe, para dividirla en 5 secciones
    # (ChrGil 2022-01-25) Esas cinco secciones son como las pide STP:
    # (ChrGil 2022-01-25) stp, region, prefijo_cliente, centro_costos, cliente_final
    def _split_cuenta_clabe(self, cuenta_clabe: List, index: int = 0, number_jumps: int = 0, section: str = ""):
        if number_jumps == 17:
            return None

        if number_jumps not in self._jumps:
            number_jumps += 1
            return self._split_cuenta_clabe(cuenta_clabe, index, number_jumps)

        if index <= number_jumps:
            section += cuenta_clabe[index]
            index += 1
            return self._split_cuenta_clabe(cuenta_clabe, index, number_jumps, section)

        number_jumps += 1
        self._list_section_clabe.append(section)
        return self._split_cuenta_clabe(cuenta_clabe, index, number_jumps)

    def _increase_number(self) -> NoReturn:
        _increase = int(self._list_section_clabe.pop()) + 1

        if _increase > 9999:
            raise ValueError('Solo es posible generar 9999 cuentas clabe, con su cuenta actual')

        self._list_section_clabe.append(f"{_increase:04d}")
        self.clabe = "".join(self._list_section_clabe)


class GenerateNewClabeSTP:
    clabe: ClassVar[str]
    clabe_stp: ClassVar[str] = PREFIX_STP_BECPOLIMENTES

    def __init__(self, razon_social_id: int):
        self._razon_social_id = razon_social_id
        clabe = self._render_clabe(clabe=self._get_last_cuentaclabe.get('cuentaclave'))
        self.clabe = self._generate_new_cuentaclabe(clabe)

    def _render_clabe(self, clabe: str):
        if 'PPCE' in clabe:
            return clabe.replace('PPCE', self.clabe_stp)
        return clabe

    @property
    def _get_last_cuentaclabe(self) -> Dict[str, Any]:
        return cuenta.objects.select_related().filter(
            persona_cuenta_id=self._razon_social_id).values('cuentaclave').order_by('fecha_creacion').first()

    # (ChrGil 2022-01-25) Válida de manera recursiva que la cuenta clabe no exista en la base de datos
    @staticmethod
    def _generate_new_cuentaclabe(clabe: str) -> str:
        nueva_clabe = VerificationAlgorithmClabe(GenerateClabe(clabe).clabe).exceute
        if cuenta.objects.filter(cuentaclave=nueva_clabe).exists():
            return gerate_new_cuenta_clabe(nueva_clabe)
        return nueva_clabe


# (ChrGil 2022-01-25) Válida de manera recursiva que la cuenta clabe no exista en la base de datos
def gerate_new_cuenta_clabe(clabe: str) -> str:
    nueva_clabe = VerificationAlgorithmClabe(GenerateClabe(clabe).clabe).exceute
    if cuenta.objects.filter(cuentaclave=nueva_clabe).exists():
        return gerate_new_cuenta_clabe(nueva_clabe)
    return nueva_clabe
