import datetime
import io
from django.db import models
from PyPDF2 import PdfFileWriter, PdfFileReader
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from django.http import FileResponse
from reportlab.lib.colors import HexColor

from apps.solicitudes.models import Solicitudes
from apps.users.management import filter_data_or_return_none, filter_all_data_or_return_none
from apps.users.models import documentos
from django.core.files import File


def get_number_attempts(person_id, instance, tipoSolicitud):
    """ Retorna el numero de intentos de una solicitud """

    intentos = 1
    filter_all_querys = filter_all_data_or_return_none(instance, tipoSolicitud_id=tipoSolicitud,
                                                       personaSolicitud_id=person_id)
    get_query = filter_data_or_return_none(instance, tipoSolicitud_id=tipoSolicitud, personaSolicitud_id=person_id)

    if get_query:
        """ Incrementamos de uno en uno """
        intentos += get_query.intentos

    for i in filter_all_querys:
        """ Eliminamos todos las solicitudes anteriores """
        i.delete()

    return intentos


def GenerarPDFSaldos(persona_saldo, cuenta, monto_total, referencia):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    # pdfmetrics.registerFont(TTFont('Roboto', 'Roboto-Regular.ttf'))
    can.setFillColor(HexColor('#5c5a59'))
    # an.setFont('Roboto', 20.5)
    can.setFontSize(20)
    can.drawString(143, 462, str(cuenta['cuentaclave']))
    can.drawString(143, 413, f'$' + str(monto_total))
    can.drawString(30, 326, referencia)
    can.save()
    packet.seek(0)
    new_pdf = PdfFileReader(packet)
    existing_pdf = PdfFileReader(open("TEMPLATES/web/FichaDeposito-SaldoDispersa.pdf", "rb"))
    output = PdfFileWriter()
    page = existing_pdf.getPage(0)
    page.mergePage(new_pdf.getPage(0))
    output.addPage(page)
    outputStream = open("TMP/web/FichaDeposito-SaldoDispersa-completo.pdf", "wb")
    output.write(outputStream)
    outputStream.close()
    documento = SubirDocumentoSaldo(persona_saldo)
    return FileResponse(packet, as_attachment=True,
                        filename='TMP/web/FichaDeposito-SaldoDispersa-completo.pdf'), documento


def SubirDocumentoSaldo(persona_saldo):
    with open('TMP/web/FichaDeposito-SaldoDispersa-completo.pdf', 'rb') as document:
        instance = documentos.objects.filter(person_id=persona_saldo, tdocumento_id=17, historial=False)
        for inst in instance:
            inst.historial = True
            inst.save()

        instance_document = documentos.objects.create(person_id=persona_saldo, comentario="Documento de saldos",
                                                      documento="",
                                                      tdocumento_id=17, historial=False)
        instance_document.documento = File(document)
        instance_document.save()

    return instance_document.id


def Sumarsolicitud(perSol: int, tipoSol: int):
    try:
        intento = Solicitudes.objects.values('intentos').get(personaSolicitud_id=perSol, tipoSolicitud_id=tipoSol,
                                                             estado_id=1)
        intento = intento['intentos'] + 1
        Solicitudes.objects.filter(personaSolicitud_id=perSol, estado_id=1).update(intentos=intento)
        return intento
    except Exception as ex:
        raise Exception("Solicitud no encontrada")


# (AAF 04-02-2021) se añade el registro de la persona quien autoriza la solicitud
def AceptarSolicitud(solicitud_id: int, admin_id=None):
    try:
        solInstance = Solicitudes.objects.get(id=solicitud_id)
        solInstance.estado_id = 4
        if not admin_id:
            solInstance.fechaChange = datetime.datetime.now()
            solInstance.personChange_id = admin_id
        solInstance.save()
    except Exception as ex:
        raise Exception("Solicitud no encontrada")
    return solInstance


# (AAF 04-02-2021)
def DevolverSolicitud(idSol: int, perSol: int):
    try:
        intento = Solicitudes.objects.values('intentos').get(id=idSol, personaSolicitud_id=perSol)
        Solicitudes.objects.filter(id=idSol, personaSolicitud_id=perSol).update(estado_id=2)
        return intento
    except Exception as ex:
        raise Exception("Solicitud no encontrada")


def ValidaSolicitud(idSol: int):
    try:
        sol = Solicitudes.objects.get_Sol(idSol)
        return sol
    except:
        raise Exception("Solicitud no encontrada")


def changueStatusRequest(request_id: int, cost_center_id: int):
    request = Solicitudes.objects.get(id=request_id, personaSolicitud_id=cost_center_id)
    request.estado_id = 11
    request.save()

# (AAF 04-02-2021) intento de cambio de status general  en prueba
def changeStatusRequest(request_id: int, personSol: int, adminSol: int, status: int, comment: str):
    request = Solicitudes.objects.get(id=request_id, personaSolicitud_id=personSol)
    request.estado_id = status
    if request.intentos >= 3 and request.estado_id == 3 and status == 3:
        request.estado_id = 9
        request.intentos += 1
    if status == 3:
        request.estado_id = 2
        request.intentos += 1
    if comment!=None or comment!="":
        request.referencia = request.referencia + comment
    request.fechaChange = datetime.datetime.now()
    request.personChange_id = adminSol
    request.save()
