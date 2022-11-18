from typing import Dict, Any, ClassVar

from rest_framework.serializers import ValidationError

import suds
import xmltodict
from apps.services_pay.management import generate_ticket
import xlrd
import datetime as dt

from polipaynewConfig.settings import SOAP_HOST_RED_EFECTIVA, COMERCIO, S_SUCURSAL, CORRESPONSAL, S_CAJA, S_CODIGO


def oEcho():
    try:
        url = SOAP_HOST_RED_EFECTIVA
        client = suds.client.Client(url)
        Mensaje = ""
        respuesta = client.service.echo(1, "sinSucursal", 438, "SandBox06", "MQ4DE78H", Mensaje)
        return respuesta
    except Exception as error:
        message_document_error = {
            "code": [400],
            "status": "ERROR",
            "detail": [
                {
                    "data": "",
                    "field": "",
                    "message": "Error al hacer la peticion a la API de red efectiva: " + str(error),
                }
            ]
        }
        raise ValidationError(message_document_error)


def datos_se_envia_red_efectiva(**kwargs):
    return {
        "Comercio": kwargs.get('Comercio', 1),
        "sSucursal": kwargs.get('sSucursal', ""),
        "Corresponsal": kwargs.get('Corresponsal', 438),
        "sCaja": kwargs.get('sCaja', "SandBox06"),
        "sCodigo": kwargs.get('sCodigo', "MQ4DE78H"),
        "TranType": kwargs.get('TranType', ""),
        "Emisor": kwargs.get('Emisor', ""),
        "Importe": kwargs.get('Importe', 0),
        "Comision": kwargs.get('Comision', 0),
        "Cargo": kwargs.get('Cargo', 0),
        "sRef1": kwargs.get('sRef1', ""),
        "sRef2": kwargs.get('sRef2', ""),
        "sRef3": kwargs.get('sRef3', ""),
        "sTicket": kwargs.get('sTicket'),
        "sOperador": kwargs.get('sOperador', ""),
        "sSku": kwargs.get('sSku', ""),
        "sEntryMode": kwargs.get('sEntryMode', "")
    }


class LogRedEfectiva:
    cat_tran_type: ClassVar[Dict[str, Any]] = {
        "10": "ABONO TIEMPO AIRE",
        "30": "CONSULTA DE SALDO",
        "31": "PAGO DE SERVICIO",
        "32": "INFORMACIÓN DE SERVICIO",
    }

    def get_tran_type(self, **kwargs):
        return self.cat_tran_type.get(str(kwargs.get('TranType')))

    @staticmethod
    def request(**kwargs) -> Dict[str, Any]:
        return {
            "Comercio": kwargs.get('Comercio', 1),
            "sSucursal": kwargs.get('sSucursal', ""),
            "Corresponsal": kwargs.get('Corresponsal', 438),
            "sCaja": kwargs.get('sCaja', "SandBox06"),
            "sCodigo": kwargs.get('sCodigo', "MQ4DE78H"),
            "TranType": kwargs.get('TranType', ""),
            "Emisor": kwargs.get('Emisor', ""),
            "Importe": kwargs.get('Importe', 0),
            "Comision": kwargs.get('Comision', 0),
            "Cargo": kwargs.get('Cargo', 0),
            "sRef1": kwargs.get('sRef1', ""),
            "sRef2": kwargs.get('sRef2', ""),
            "sRef3": kwargs.get('sRef3', ""),
            "sTicket": kwargs.get('ticket'),
            "sOperador": kwargs.get('sOperador', ""),
            "sSku": kwargs.get('sSku', ""),
            "sEntryMode": kwargs.get('sEntryMode', "")
        }

    @staticmethod
    def response(respuesta: Any) -> str:
        return str(respuesta)


class CreateDocumentLogEfectiva:
    def __init__(self, log: LogRedEfectiva, request: Dict[str, Any], response: Any, **kwargs):
        self.log = log
        self.request = request
        self.response = response
        self.ticket = kwargs.get('ticket')
        self.time_request = kwargs.get('date1')
        self.time_response = kwargs.get('date2')
        self.create_document()

    def create_document(self):
        with open('pruebas_log.txt', 'a') as file:
            file.write(f"{self.log.get_tran_type(**self.request)}\n\n")
            file.write(f"--------> REQUEST [{self.time_request}]\n\n")
            for k, v in self.log.request(ticket=self.ticket, **self.request).items():
                file.write(f"\t{k}: {v}\n")

            file.write(f"\n\n--------> RESPONSE [{self.time_response}]\n\n")
            file.write(f"{self.log.response(self.response)}")
            file.write("\n\n")


def solicita(request: dict):
    try:
        url = SOAP_HOST_RED_EFECTIVA
        client = suds.client.Client(url)
        ticket = generate_ticket()
        date1 = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        respuesta = client.service.solicita(
            Comercio=COMERCIO,  # Comercio Variable global
            sSucursal=S_SUCURSAL,  # sSucursal
            Corresponsal=CORRESPONSAL,  # Corresponsal variable global
            sCaja=S_CAJA,  # sCaja variable global
            sCodigo=S_CODIGO,  # sCodigo  variable global
            TranType=request["TranType"] if "TranType" in request.keys() else "",  # TranType
            Emisor=request["Emisor"] if "Emisor" in request.keys() else "",  # Emisor
            Importe=request["Importe"] if "Importe" in request.keys() else 0,  # Importe
            Comision=request["Comision"] if "Comision" in request.keys() else 0,  # Comision
            Cargo=request["Cargo"] if "Cargo" in request.keys() else 0,  # Cargo
            sRef1=request["sRef1"] if "sRef1" in request.keys() else "",  # sRef1
            sRef2=request["sRef2"] if "sRef2" in request.keys() else "",  # sRef2
            sRef3=request["sRef3"] if "sRef3" in request.keys() else "",  # sRef3
            sTicket=ticket,  # sTicket descomentar al crear el registro en la base de datos
            sOperador=request["sOperador"] if "sOperador" in request.keys() else "",  # sOperador
            sSku=request["sSku"] if "sSku" in request.keys() else "",  # sSku
            sEntryMode=request["sEntryMode"] if "sEntryMode" in request.keys() else ""
        )

        date2 = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_efectiva = LogRedEfectiva()
        CreateDocumentLogEfectiva(log_efectiva, request, respuesta, date1=date1, date2=date2, ticket=ticket)

        # Para Informacion de servicio
        if respuesta.solicitaResult == 0:

            # Consultar saldo y consultar info emisor
            if request["TranType"] == 32 or request["TranType"] == 30:

                # diccionario de respuesta de info3
                dict_xml_info3 = xmltodict.parse(respuesta.info3)
                respuesta.info3 = dict_xml_info3  # reescribir esa llave con la informacion convertida a diccionario

            # para Recarga de saldo y pago de salgo
            if request["TranType"] == 10 or request["TranType"] == 31:

                # Consultar saldo y consultar info emisor, # diccionario de respuesta de MsgTicket
                dict_xml_MsgTicket = xmltodict.parse(respuesta.MsgTicket.replace("</MSG>", "</Msg>"))

                # reescribir esa llave con la informacion convertida a diccionario
                respuesta.MsgTicket = dict_xml_MsgTicket

        return respuesta, ticket
    except Exception as error:
        message_document_error = {
            "status": "Error al hacer la peticion a la API de red efectiva"
        }
        raise ValidationError(message_document_error)


def test_matrix():
    filePath = "/home/eduardo/Documents/Polimentes/General .xlsx"
    openFile = xlrd.open_workbook(filePath)
    sheet = openFile.sheet_by_name("Matriz Servicios ")
    sheet2 = openFile.sheet_by_name("Tiempo Aire - Dat")
    textFile = open('/home/eduardo/Documents/Polimentes/resultmatrix.txt', 'w')
    for i in range(sheet2.nrows):
        trantype = sheet2.cell_value(i, 7)
        if trantype == 10:
            sref1 = str(sheet2.cell_value(i, 0)).replace("'", "")
            sref1 = sref1.replace(".0", "")
            importe = float(sheet2.cell_value(i, 3)) * 10
            importe = int(str(importe * 10).replace(".0", ""))
            emisor = int(sheet2.cell_value(i, 2))
            request = {
                    "Comercio": 1,
                    "Corresponsal": 438,
                    "sCaja": "SandBox06",
                    "sCodigo": "MQ4DE78H",
                    "TranType": 10,
                    "Emisor": emisor,
                    "Importe": importe,
                    "sRef1": sref1,
                    "sTicket": 3000+i
                    }
            response, ticket = solicita(request)
            textFile.write(str(request))
            textFile.write(str(response))
            textFile.write("\n")
            print(response)

    for i in range(sheet.nrows):
        trantype = sheet.cell_value(i,7)
        if trantype == 31:
            sref1 = str(sheet.cell_value(i, 0)).replace("'", "")
            sref1 = sref1.replace(".0", "")
            importe = float(sheet.cell_value(i, 3))*100
            importe = int(str(importe).replace(".0", ""))
            emisor = int(sheet.cell_value(i, 2))
            comision = int(str(float(sheet.cell_value(i, 4)) * 100).replace(".0", ""))
            cargo = int(str(float(sheet.cell_value(i, 5)) * 100).replace(".0", ""))
            request = {
                    "Comercio": 1,
                    "Corresponsal": 438,
                    "sCaja": "SandBox06",
                    "sCodigo": "MQ4DE78H",
                    "TranType": 31,
                    "Emisor": emisor,
                    "Importe": importe,
                    "Comision": comision,
                    "Cargo": cargo,
                    "sRef1": sref1,
                    "sTicket": 3200+i
                    }
            response, ticket = solicita(request)
            textFile.write(str(request))
            textFile.write(str(response))
            textFile.write("\n")
            print(response)
        if trantype == 30:
            sref1 = str(sheet.cell_value(i, 0)).replace("'", "")
            sref1 = sref1.replace(".0", "")
            emisor = int(sheet.cell_value(i, 2))
            request = {
                    "Comercio": 1,
                    "Corresponsal": 438,
                    "sCaja": "SandBox06",
                    "sCodigo": "MQ4DE78H",
                    "TranType": 30,
                    "Emisor": emisor,
                    "sRef1": sref1,
                    }
            response, ticket = solicita(request)
            textFile.write(str(request))
            textFile.write(str(response))
            textFile.write("\n")
            print(response)
        if trantype == "30-31":
            sref1 = str(sheet.cell_value(i, 0)).replace("'", "")
            sref1 = sref1.replace(".0", "")
            importe = float(sheet.cell_value(i, 3))*10
            importe = int(str(importe*10).replace(".0", ""))
            emisor = int(sheet.cell_value(i, 2))
            comision = int(str(float(sheet.cell_value(i, 4)) * 100).replace(".0", ""))
            cargo = int(str(float(sheet.cell_value(i, 5)) * 100).replace(".0", ""))
            request31 = {
                    "Comercio": 1,
                    "Corresponsal": 438,
                    "sCaja": "SandBox06",
                    "sCodigo": "MQ4DE78H",
                    "TranType": 31,
                    "Emisor": emisor,
                    "Importe": importe,
                    "Comision": comision,
                    "Cargo": cargo,
                    "sRef1": sref1,
                    "sTicket": 3500+i
                    }
            request30 = {
                "Comercio": 1,
                "Corresponsal": 438,
                "sCaja": "SandBox06",
                "sCodigo": "MQ4DE78H",
                "TranType": 30,
                "Emisor": emisor,
                "sRef1": sref1,
            }
            response31, ticket = solicita(request31)
            textFile.write(str(request31))
            textFile.write(str(response31))
            textFile.write("\n")
            print(response31)
            response30, ticket = solicita(request30)
            textFile.write(str(request30))
            textFile.write(str(response30))
            textFile.write("\n")
            print(response30)
    textFile.close()
