import io
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, ClassVar, List, Union

from PyPDF2 import PdfFileReader, PdfFileWriter
from barcode import EAN13, Code128
from barcode.writer import ImageWriter
from django.core.files import File

from django.db.models import Q
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet

from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from MANAGEMENT.Utils.utils import generate_value_paycash_with_uuid
from apps.logspolipay.manager import RegisterLog
from apps.paycash.models import PayCashReference, PayCashRegistraNotificacionPago
from apps.paycash.paycash_api.client import APIGetTokenPayCash, APICreateReferencePayCash, APICancelReferencePayCash
from apps.paycash.paycash_api.exceptions import PayCashException
from apps.paycash.platform.mobile.serializers.serializers import SerializerCreateReference
from apps.suppliers.models import cat_products_params, cat_supplier
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Standard.success_responses import MyHtppSuccess
from apps.users.models import persona, cuenta
import datetime as dt


class ComponenGetTokenPayCash:
    def __init__(self):
        token = self.get_token_autorization_paycash

        if token:
            json_content: Dict = json.loads(token.get("json_content"))
            self.autorization = json_content.get("Authorization", None)

    @property
    def get_token_autorization_paycash(self) -> Union[Dict[str, Any], None]:
        return cat_products_params.objects.filter(supplier_id=1).values("id", "json_content").last()


@dataclass
class ComponentSaveTokenPayCash:
    token: APIGetTokenPayCash
    _default_suppliers: ClassVar[int] = "PayCash"

    def __post_init__(self):
        suppliers = self.get_supplier

        if suppliers:
            self.suppliers = suppliers
            self.delete_old_token()
            self.create()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "proveedor_id": self.suppliers.get("id"),
            "response": self.token.response
        }

    @property
    def get_supplier(self) -> Dict[str, Any]:
        return cat_supplier.objects.get_supplier(name=self._default_suppliers, short_name=self._default_suppliers)

    def delete_old_token(self):
        old_token: List[cat_products_params] = cat_products_params.objects.filter(supplier_id=self.suppliers.get("id"))
        if old_token:
            for row in old_token:
                row.delete()

    def create(self):
        cat_products_params.objects.create_params(**self._data)


# (ChrGil 2022-06-15) Guarda en la base de datos el token mas actual de paycash
class TokenPayCash(RetrieveAPIView):
    _token: ClassVar[APICreateReferencePayCash] = APIGetTokenPayCash
    permission_classes = ()

    def retrieve(self, request, *args, **kwargs):
        log = RegisterLog(-1, request)
        log.json_request({})
        try:
            with atomic():
                token = self._token()
                ComponentSaveTokenPayCash(token)
        except PayCashException as e:
            err = MyHttpError(message=e.msg, code=int(e.code), real_error=None)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess(message="Consulta exitosa", code="200")
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


class CreateReferenceRequestDataPayCash:
    def __init__(self, request_data: Dict[str, Any]):
        self.request_data = request_data

    @property
    def get_amount(self) -> float:
        return self.request_data.get("Amount")

    @property
    def get_payment_concept(self) -> str:
        return self.request_data.get("PaymentConcept")

    @property
    def get_expiration_date(self) -> str:
        return self.request_data.get("ExpirationDate")

    @property
    def get_type(self) -> bool:
        return self.request_data.get("Type")

    @property
    def get_comission_pay(self) -> float:
        return self.request_data.get("CommissionPay")

    @property
    def get_token(self) -> str:
        return self.request_data.get("Token")


@dataclass
class ValidateToken:
    request_data: CreateReferenceRequestDataPayCash
    user: persona

    def __post_init__(self):
        token = self._decrypt_token
        self.raise_error(token)

    def raise_error(self, token: Dict[str, Any]):
        if self.request_data.get_token != token.get("data"):
            raise ValueError("Token de autorización no valido")

    @property
    def _decrypt_token(self) -> Dict[str, Any]:
        return encdec_nip_cvc_token4dig(accion="2", area="BE", texto=self.user.token)


class UserInfo:
    def __init__(self, user: persona):
        self._user = user
        info = self.get_info

        if info:
            self.info = info

        if not info:
            raise ValueError("Su cuenta no se encuentra activa o fue dada de baja")

    @property
    def get_info(self) -> Dict[str, Any]:
        return cuenta.objects.get_info_with_user_id(owner=self._user.get_only_id())


class APICreateReference:
    _reference_api: ClassVar[APICreateReferencePayCash] = APICreateReferencePayCash

    def __init__(self, request_data: CreateReferenceRequestDataPayCash):
        self._request_data = request_data
        self.raise_error()
        self.value = self._generate_value_clave_rastreo_paycash
        self.reference_api = self._reference_api(**self._data)

    def raise_error(self):
        if self._request_data.get_amount < 0:
            raise ValueError("El monto que ingresó no es válido")

        if self._request_data.get_amount > 20_000:
            raise ValueError(f"El monto máximo para crear una referencia es de $20,000")

        if dt.datetime.strptime(self._request_data.get_expiration_date, "%Y-%m-%d").date() <= dt.date.today():
            raise ValueError("Fecha Vigencia Invalida")

    @property
    def _generate_value_clave_rastreo_paycash(self) -> str:
        return generate_value_paycash_with_uuid()

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "expire_date": self._request_data.get_expiration_date,
            "amount": self._request_data.get_amount,
            "value": self.value,
            "type": self._request_data.get_type,
        }


class CreateReference:
    _serializer_class: ClassVar[SerializerCreateReference] = SerializerCreateReference
    _supplier: ClassVar[int] = 1
    _cat_type_page: ClassVar[Dict[str, Any]] = {
        True: 1,
        False: 2
    }

    def __init__(self, request_data: CreateReferenceRequestDataPayCash, user: UserInfo, reference: APICreateReference):
        self._request_data = request_data
        self._user = user
        self._reference = reference
        self.reference_id = self.create

    @property
    def _data(self) -> Dict[str, Any]:
        return {
            "value": self._reference.value,
            "supplier_id": self._supplier,
            "amount": self._request_data.get_amount,
            "expiration_date": self._request_data.get_expiration_date,
            "payment_concept": self._request_data.get_payment_concept,
            "persona_cuenta_id": self._user.info.get("id"),
            "type_reference_id": self._cat_type_page.get(self._request_data.get_type),
            "reference_number": self._reference.reference_api.response.get("Reference"),
            "comission_pay": self._request_data.get_comission_pay,
        }

    @property
    def create(self) -> int:
        serializer = self._serializer_class(data=self._data)
        serializer.is_valid(raise_exception=True)
        reference_id = serializer.create()
        return reference_id


@dataclass
class GetReferenceInfo:
    reference: CreateReference

    def __post_init__(self):
        self.reference_data = self.get_reference_info

    @property
    def get_reference_info(self) -> Dict[str, Any]:
        return PayCashReference.objects.detail_reference(self.reference.reference_id)


@dataclass
class CreateReferenceBarcode:
    reference: GetReferenceInfo

    def __post_init__(self):
        reference_number = self.reference.reference_data.get("reference_number")
        self.filename_barcode = self._create_barcode(reference_number)

    @staticmethod
    def _create_barcode(reference_number: str) -> str:
        with open(f'{reference_number}.png', 'wb') as f:
            Code128(reference_number, writer=ImageWriter()).write(f)
            return f.name


class LiftPackage:
    def __init__(self):
        _packet = io.BytesIO()
        self.packet = _packet
        self.pdf = canvas.Canvas(_packet, pagesize=letter)


class PDFCoordinatesPayCash:
    def __init__(self, file: LiftPackage, reference: CreateReferenceBarcode, reference_data: GetReferenceInfo):
        self.concepto_pago = reference_data.reference_data.get("payment_concept")
        self.servicio = reference_data.reference_data.get("supplier__name_large")
        self.monto = f"${reference_data.reference_data.get('amount'):3,.2f}"
        self.reference_file_name = reference.filename_barcode
        self.pdf = file.pdf

        self.draw_string(x=45, y=2510, text=self.concepto_pago[0:39])
        if len(self.concepto_pago) > 39:
            self.draw_string(x=45, y=2490, text=self.concepto_pago[39:80])

        self.draw_string(x=45, y=2412, text=self.servicio)
        self.draw_string(x=45, y=2330, text=self.monto)
        self.draw_image(image=self.reference_file_name, x=88, y=2115, height=130, width=240)
        self.save()

    def draw_string(self, x: float, y: float, text: Any):
        self.pdf.drawString(x, y, text)

    def draw_image(self, image: str, x: float, y: float, height: float, width: float):
        self.pdf.drawImage(image=image, x=x, y=y, height=height, width=width)

    def save(self):
        self.pdf.save()


class StylesPDF:
    _font_name: ClassVar[str] = "Montserrat"
    _font_location: ClassVar[str] = 'TEMPLATES/FONTS/Montserrat-Light.ttf'
    _color_font_hex: ClassVar[str] = "#3A555B"
    _font_size: ClassVar[float] = 16.0

    def __init__(self, file: LiftPackage):
        self.file = file
        self.set_styles()

    def set_styles(self):
        pdfmetrics.registerFont(TTFont(self._font_name, self._font_location))
        self.file.pdf.setFont(self._font_name, self._font_size)
        self.file.pdf.setFillColor(HexColor(val=self._color_font_hex))


class PayCashCreatePDF:
    _template_pdf: ClassVar[str] = "TEMPLATES/web/Referencia_PayCash.pdf"
    _new_pdf_file: ClassVar[PdfFileReader] = PdfFileReader
    _read_template_pdf: ClassVar[PdfFileReader] = PdfFileReader

    def __init__(self, file: LiftPackage, reference: GetReferenceInfo, reference_barcode: CreateReferenceBarcode):
        self.file = file
        self.reference_barcode = reference_barcode
        reference_number = reference.reference_data.get("reference_number")

        new_pdf = self._new_pdf_file(self.file.packet)
        existing_pdf = self._read_template_pdf(open(self._template_pdf, "rb"))
        page = existing_pdf.getPage(0)
        page.mergePage(new_pdf.getPage(0))

        _output_file = PdfFileWriter()
        _output_file.addPage(page)
        with open(f"TMP/web/PayCashReference/referencia_paycash_user_id_{reference_number}.pdf", "wb") as f:
            _output_file.write(f)
            self.filename = f.name


class UpDocumentReference:
    def __init__(self, reference: GetReferenceInfo, barcode: CreateReferenceBarcode, pdf: PayCashCreatePDF):
        self.reference = reference
        self.barcode = barcode
        self.pdf = pdf
        self.aws_url = self.update

    @property
    def update(self) -> str:
        filename_pdf = self.pdf.filename
        filename_barcode = self.barcode.filename_barcode

        instance: PayCashReference = PayCashReference.objects.get(id=self.reference.reference_data.get("id"))

        with open(filename_pdf, 'rb') as document:
            instance.barcode = File(document)
            instance.save()

        os.remove(filename_pdf)
        os.remove(filename_barcode)
        return instance.get_url_aws_document


class ResponseSuccess:
    def __init__(self, reference: GetReferenceInfo, document: UpDocumentReference):
        self.reference = reference
        self.resonse = self.render_response(**reference.reference_data, url_file=document.aws_url)

    @staticmethod
    def render_response(url_file: str, **kwargs) -> Dict[str, Any]:
        return {
            "id": kwargs.get("id"),
            "Service": kwargs.get("supplier__name_large"),
            "ReferenceNumber": kwargs.get("reference_number"),
            "PaymentConcept": kwargs.get("payment_concept"),
            "Amount": kwargs.get("amount"),
            "TypeReference": kwargs.get("type_reference__type_reference"),
            "FileBarcode": url_file,
        }


class CreateReferencePayCash(GenericViewSet):
    _response: ClassVar[ResponseSuccess] = ResponseSuccess
    _create_reference: ClassVar[CreateReference] = CreateReference
    _request_data: ClassVar[CreateReferenceRequestDataPayCash] = CreateReferenceRequestDataPayCash
    _reference_api: ClassVar[APICreateReference] = APICreateReference
    _package: ClassVar[LiftPackage] = LiftPackage
    _styles: ClassVar[StylesPDF] = StylesPDF
    _coordinates: ClassVar[PDFCoordinatesPayCash] = PDFCoordinatesPayCash
    _create_pdf: ClassVar[PayCashCreatePDF] = PayCashCreatePDF
    _up_document: ClassVar[UpDocumentReference] = UpDocumentReference
    _token: ClassVar[ValidateToken] = ValidateToken
    _user_info: ClassVar[UserInfo] = UserInfo
    _log: ClassVar[RegisterLog] = RegisterLog

    def create(self, request):
        user: persona = request.user
        log = self._log(user, request)
        log.json_request(request.data)
        try:
            with atomic():
                request_data = self._request_data(request.data)
                self._token(request_data, user)
                user_info = self._user_info(user)
                api = self._reference_api(request_data)
                create_reference = CreateReference(request_data, user_info, api)
                reference_info = GetReferenceInfo(create_reference)
                barcode = CreateReferenceBarcode(reference_info)

                package = self._package()
                self._styles(package)
                self._coordinates(package, barcode, reference_info)
                pdf = self._create_pdf(package, reference_info, barcode)
                file = self._up_document(reference_info, barcode, pdf)
                response = self._response(reference_info, file)

        except PayCashException as e:
            err = MyHttpError(message=e.msg, real_error=e.msg)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, KeyError) as e:
            err = MyHttpError(message=str(e), real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess("La referencia se creó con éxito", extra_data=response.resonse)
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


class ComponentReference:
    def __init__(self, reference_id: int):
        self.reference_id = reference_id
        reference = self.get_reference

        if reference:
            self.reference = reference

        if not reference:
            raise ValueError("Referencia no encontrada o la operación ha sido previamente cancelada")

    @property
    def get_reference(self) -> Dict[str, Any]:
        return PayCashReference.objects.filter(
            id=self.reference_id,
            status_reference_id=3
        ).values(
            "id",
            "reference_number"
        ).first()


class CangeStatusReference:
    def __init__(self, reference_id: int, status_reference_id: int):
        self.reference_id = reference_id
        self.update_reference(reference_id=reference_id, status_reference_id=status_reference_id)

    @staticmethod
    def update_reference(reference_id: int, **kwargs):
        PayCashReference.objects.update_reference(
            reference_id=reference_id,
            date_cancel=dt.datetime.now(),
            date_modify=dt.datetime.now(),
            **kwargs
        )


class CancelReferencePayCash(RetrieveAPIView):
    _reference: ClassVar[ComponentReference] = ComponentReference
    _reference_api: ClassVar[APICancelReferencePayCash] = APICancelReferencePayCash
    _log: ClassVar[RegisterLog] = RegisterLog
    _change_status: ClassVar[CangeStatusReference] = CangeStatusReference

    def retrieve(self, request, *args, **kwargs):
        user: persona = request.user
        log = self._log(user, request)
        log.json_request(self.request.query_params)

        try:
            reference_id: int = self.request.query_params.get("reference_id")
            reference_instance = self._reference(reference_id)
            self._reference_api(**reference_instance.get_reference)
            self._change_status(reference_id, 5)

        except PayCashException as e:
            err = MyHttpError(message=e.msg, real_error=e.msg)
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, KeyError) as e:
            err = MyHttpError(message=str(e), real_error=str(e))
            log.json_response(err.standard_error_responses())
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
        else:
            succ = MyHtppSuccess("La referencia ha sido cancelada")
            log.json_response(succ.standard_success_responses())
            return Response(succ.standard_success_responses(), status=status.HTTP_200_OK)


class ListReferences:
    _default_status: ClassVar[List[int]] = [3, 5, 1]

    def __init__(self, user: persona, **kwargs):
        self.user = user.get_only_id()
        self.start_date = kwargs.get("start_date", dt.date.today() - dt.timedelta(days=91))
        self.end_date = kwargs.get("end_date", dt.date.today())
        self.status = kwargs.get("status", self._default_status)
        self.list = [self._render_data(**row) for row in self._list]

    @property
    def _list(self) -> List[Dict[str, Any]]:
        return PayCashReference.objects.list_reference(
            start_date=self.start_date,
            end_date=self.end_date,
            user=self.user,
            status=self.status
        )

    @staticmethod
    def _render_data(**kwargs) -> Dict[str, Any]:
        return {
            "id": kwargs.get("id"),
            "Amount": kwargs.get("amount"),
            "ReferenceNumber": kwargs.get("reference_number"),
            "PaymentConcept": kwargs.get("payment_concept"),
            "DateCreated": kwargs.get("date_modify"),
            "TypeReferenceId": kwargs.get("type_reference_id"),
            "TypeReference": kwargs.get("type_reference__type_reference"),
            "StatusReferenceId": kwargs.get("status_reference_id"),
            "StatusReference": kwargs.get("status_reference__nombre"),
            "IdPolipay": kwargs.get("value"),
        }


class ListReferencePayCash(ListAPIView):
    _list: ClassVar[ListReferences] = ListReferences

    @method_decorator(cache_page(60 * 0.1))
    def list(self, request, *args, **kwargs):
        try:
            user: persona = request.user
            data = {key: value for key, value in self.request.query_params.items() if value != 'null'}
            list_reference = self._list(user, **data)
            return Response(list_reference.list, status=status.HTTP_200_OK)

        except Exception as e:
            err = MyHttpError(message="Ocurrion un error al listar las referencias", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)


class DetailReference:
    def __init__(self, reference_id: int):
        self.reference_id = reference_id
        detail_reference = self._detail
        if not detail_reference:
            raise ValueError("Referencia no encontrada")

        if detail_reference.get("status_reference_id") == 1:
            file = self.get_file_reference
            more_detail = self._more_detail_liquided(detail_reference.get("id"))
            self.detail = self._render(**detail_reference, detail=self._render_more_detail(**more_detail), file=file)

        if detail_reference.get("status_reference_id") != 1:
            file = self.get_file_reference
            self.detail = self._render(**detail_reference, file=file)

    @property
    def _detail(self) -> Dict[str, Any]:
        return PayCashReference.objects.detail_reference(self.reference_id)

    @property
    def get_file_reference(self) -> str:
        return PayCashReference.objects.get(id=self.reference_id).get_url_aws_document

    @staticmethod
    def _more_detail_liquided(reference_id: int) -> Dict[str, Any]:
        return PayCashRegistraNotificacionPago.objects.filter(
            reference_id=reference_id
        ).values(
            "id",
            "date_created",
            "referencia",
            "reference__persona_cuenta__cuentaclave"
        ).first()

    @staticmethod
    def _render_more_detail(**kwargs):
        return {
            "id": kwargs.get("id"),
            "DateTransaction": kwargs.get("date_created"),
            "OriginAccount": kwargs.get("referencia"),
            "DestinationAccount": kwargs.get("reference__persona_cuenta__cuentaclave"),
        }

    @staticmethod
    def _render(**kwargs):
        return {
            "Monto": kwargs.get("amount"),
            "PaymentConcept": kwargs.get("payment_concept"),
            "ReferenceNumber": kwargs.get("reference_number"),
            "StatusReferenceId": kwargs.get("status_reference_id"),
            "StatusReference": kwargs.get("status_reference__nombre"),
            "DateCreated": kwargs.get("date_created"),
            "DateCancel": kwargs.get("date_cancel"),
            "FileReference": kwargs.get("file"),
            "Detail": kwargs.get("detail", None)
        }


class DetailReferencePayCash(ListAPIView):
    _detail_reference: ClassVar[DetailReference] = DetailReference

    def list(self, request, *args, **kwargs):
        try:
            reference_id: int = self.request.query_params.get("reference_id")
            reference = self._detail_reference(reference_id)
            return Response(reference.detail, status=status.HTTP_200_OK)
        except Exception as e:
            err = MyHttpError(message="Ocurrion un error al listar las referencias", real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)
