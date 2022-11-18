from dataclasses import dataclass
from typing import ClassVar, Dict, Any, Union, List

from apps.users.serializers import SerializerDocuments, SerializerGrupoPersona, SerializerCreateAccount, \
    SerializerCrearSolicitudIn, SerializerCreateAddress


# (ChrGil 2021-12-08) Desacopla el objeto JSON en metodos, para hacer mas flexible el acceso a datos
# (ChrGil 2021-12-08) Solo se utiliza para alta cliente Moral, centro de costos
@dataclass
class RequestData:
    request_data: Dict[str, Any]

    @property
    def get_razon_social(self) -> Dict[str, Union[str, int]]:
        return self.request_data.get('RazonSocial')

    @property
    def get_representante_legal(self) -> Dict[str, Union[str, int]]:
        return self.request_data.get('RepresentanteLegal')


# (ChrGil 2021-12-08) Crea una Solcitud para la apertura de un centro de costos y/o cliente moral o cualquier solicitud
@dataclass
class CrearSolicitud:
    person_id: int
    description: str
    _serializer_class: ClassVar[SerializerCrearSolicitudIn] = SerializerCrearSolicitudIn

    def execute(self) -> None:
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "nombre": self.description,
            "personaSolicitud_id": self.person_id,
            "tipoSolicitud_id": 1,
            "estado_id": 1
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2021-12-08) Se encarga de crear la relación entre personas Morales y Fisica, tambien se puede
# (ChrGil 2021-12-08) utilizar para cualquier otro caso de uso.
@dataclass
class CreateGrupoPersona:
    razon_social_id: int
    person_id: int
    relacion_grupo_id: int
    nombre_grupo: str
    _serializer_class: ClassVar[SerializerGrupoPersona] = SerializerGrupoPersona

    def execute(self) -> None:
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "empresa_id": self.razon_social_id,
            "nombre_grupo": self.nombre_grupo,
            "relacion_grupo_id": self.relacion_grupo_id
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2021-12-08) Crea la cuenta de una persona Moral, esta clase unicamente se utiliza cuando
# (ChrGil 2021-12-08) Se crea un centro de costos o un cliente Moral
@dataclass
class CreateAccountClienteMoral:
    razon_social_id: int
    cuenta_eje_id: int
    _serializer_class: ClassVar[SerializerCreateAccount] = SerializerCreateAccount

    def execute(self) -> None:
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "persona_cuenta_id": self.razon_social_id
        }

    @property
    def _context(self) -> Dict[str, Any]:
        return {
            "empresa_id": self.cuenta_eje_id
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data, context=self._context)
        serializer.is_valid(raise_exception=True)
        serializer.create()


# (ChrGil 2021-12-08) Crea apartir de un listado de documentos cualquier tipo de documento en formato PDF
# (ChrGil 2021-12-08) Actualmente es utilizado en alta centros de costos y alta cliente Moral
@dataclass
class CreateDocuments:
    person_id: int
    list_documents: List[Dict[str, Any]]
    _serializer_class: ClassVar[SerializerDocuments] = SerializerDocuments

    def execute(self) -> None:
        self._create()

    def _data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tipo": data.get('TipoDocumento'),
            "owner": self.person_id,
            "comment": data.get('Comentario'),
            "base64_file": data.get('Documento')
        }

    def _create(self):
        for data in self.list_documents:
            serializer = self._serializer_class(data=self._data(data))
            serializer.is_valid(raise_exception=True)
            serializer.create()


# (ChrGil 2021-12-08) Crea el domicilio de una persona fisica o moral, enviando la data y el id de la persona
# (ChrGil 2021-12-08) actualmente es utilizado en alta centro de costos y cliente Moral
@dataclass
class CreateAddress:
    data: Dict[str, Union[str]]
    person_id: int
    _serializer_class: ClassVar[SerializerCreateAddress] = SerializerCreateAddress

    def execute(self):
        self._create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "codigopostal": self.data.get('CodigoPostal'),
            "calle": self.data.get("Calle"),
            "no_exterior": self.data.get("NoExterior"),
            "no_interior": self.data.get("NoInterior"),
            "colonia": self.data.get("Colonia"),
            "alcaldia_mpio": self.data.get("Municipio"),
            "estado": self.data.get("Estado"),
            "pais": self.data.get("Pais"),
            "domicilioPersona_id": self.person_id
        }

    def _create(self):
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        serializer.create()
