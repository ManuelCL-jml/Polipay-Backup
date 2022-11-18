from typing import Dict, Any, ClassVar

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from polipaynewConfig import settings


class MessageEmail:
    _EMAIL_HOST: ClassVar[str] = settings.EMAIL_HOST_USER
    _template_html: ClassVar[str] = None
    _template_plaintext: ClassVar[str] = None
    _subject: ClassVar[Any] = None
    _to: ClassVar[str]
    context: ClassVar[Dict[str, Any]]

    def _email_multi_alternatives(self) -> EmailMultiAlternatives:
        return EmailMultiAlternatives(
            subject=self._subject,
            body=get_template(self._template_plaintext).render(self.context),
            from_email=self._EMAIL_HOST,
            to=[self._to]
        )

    def _attach_alternative(self):
        msg = self._email_multi_alternatives()
        msg.attach_alternative(get_template(self._template_html).render(self.context), "text/html")
        msg.send()


class EmailAuthTransactionIndividual(MessageEmail):
    _template_html: ClassVar[str] = "notificacion-movimientos.html"
    _template_plaintext: ClassVar[str] = "notificacion-movimientos.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailWelcomeColaborador(MessageEmail):
    _template_html: ClassVar[str] = "welcome_colaborador.html"
    _template_plaintext: ClassVar[str] = "welcome_colaborador.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailVerifyDocumentsCostCenter(MessageEmail):
    _template_html: ClassVar[str] = "solicitudes_verifica_cetro_costos.html"
    _template_plaintext: ClassVar[str] = "solicitudes_verifica_cetro_costos.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailWarningAdminsPolipay(MessageEmail):
    _template_html: ClassVar[str] = "warning_comission_pay.html"
    _template_plaintext: ClassVar[str] = "warning_comission_pay.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailWarningAdminsInPolipay(MessageEmail):
    """ Envio de correo cuando entra dinero a Polipay """

    _template_html: ClassVar[str] = "transaccion_recibida.html"
    _template_plaintext: ClassVar[str] = "transaccion_recibida.txt"
    _subject: ClassVar[Any] = 'Transacción Recibida'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailWarningAdminsPolipayFondeoSaldosWallet(MessageEmail):
    _template_html: ClassVar[str] = "warning_fondeo_saldos_wallet.html"
    _template_plaintext: ClassVar[str] = "warning_fondeo_saldos_wallet.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()


class EmailWarningCommissionList(MessageEmail):
    _template_html: ClassVar[str] = "warning_comission_pay_list.html"
    _template_plaintext: ClassVar[str] = "warning_comission_pay_list.txt"
    _subject: ClassVar[Any] = 'Estado de Transacción'

    def __init__(self, to: str, **kwargs):
        self._to = to
        self.context = {k: v for k, v in kwargs.items()}
        self._attach_alternative()

