from os import remove
from datetime import datetime

from django.db.models import Q
from django.core.files import File

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView

from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.web.serializers.serializers_transaction_export_file import *
from apps.users.models import persona, cuenta, documentos
from apps.transaction.models import transferencia

# CASO 01 - Transacciones Polipay a Polipay

class TransactionsPolipayToPolipay():

    def __init__(self, type=0, tmpPath="", tmpName="", csvStructure="", data=None, request=None):
        self.type           = type
        self.tmpPath        = tmpPath
        self.tmpName        = tmpName
        self.csvStructure   = csvStructure
        self.data           = data
        self.request        = request
        self.setTmpName()



    def setTmpName(self):
        if str(self.tmpName) == None or str(self.tmpName) == "":
            fhNow           = datetime.now()
            fh              = fhNow.strftime("%Y%m%d%H%m%S%s")
            nombreTmpCSV    = "UID" + str(self.request.user.id) + "T" + str(fh) + ".csv"
            self.tmpName    = "TMP/ExportCSV/" + str(nombreTmpCSV)



    def _validateEmp(self, company_id):
        r   = None
        queryExisteEmpresa = persona.objects.filter(id=int(company_id)).exists()
        if not queryExisteEmpresa:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "company_id",
                        "data": str(company_id),
                        "message": "No existe la empresa."
                    }
                ]
            }
        return r

    def _getData(self, data):
        queryMovimientos = None

        # Cofirmo que existe empres
        r   = self._validateEmp(data["company_id"])
        if r != None:
            if int(r["code"][0]) == 400:
                return r

        # Recupero cuenta y clabe de la empresa
        queryCuentaCLABE = cuenta.objects.filter(persona_cuenta_id=int(data["company_id"])).values("id", "cuenta",
                                                                                                   "cuentaclave")

        # Recupero movimientos
        dataFilter = {}

        if(data["filter"] == None or str(data["filter"]) == "null" or str(data["filter"]) == "false") and \
            (data["payment_type"] == None or str(data["payment_type"]) == "null" or str(data["payment_type"]) == "false"):
            #print("IF Todo nulll")
            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                Q(cta_beneficiario=queryCuentaCLABE[0]["cuenta"]) | Q(cta_beneficiario=queryCuentaCLABE[0]["cuentaclave"]),
                tipo_pago_id=1).values("id", "cuenta_emisor", "nombre_emisor",
                                       "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                                       "concepto_pago", "tipo_pago__nombre_tipo",
                                       "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                                       "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor",
                                       "referencia_numerica", "email")

        # Enviadas
        elif(data["filter"] == None or str(data["filter"]) == "null" or str(data["filter"]) == "false") and \
            (int(data["payment_type"]) == 1):
            #print("IF Enviadas")
            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                Q(status_trans_id=1) | Q(status_trans_id=3), tipo_pago_id=1).values("id", "cuenta_emisor", "nombre_emisor",
                                       "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                                       "concepto_pago", "tipo_pago__nombre_tipo",
                                       "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                                       "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor",
                                       "referencia_numerica", "email")

        # Recibidas
        elif(data["filter"] == None or str(data["filter"]) == "null" or str(data["filter"]) == "false") and \
            (int(data["payment_type"]) == 8):
            #print("IF Todo Recibidas")
            queryMovimientos = transferencia.objects.filter(
                Q(cta_beneficiario=queryCuentaCLABE[0]["cuenta"]) | Q(cta_beneficiario=queryCuentaCLABE[0]["cuentaclave"]),
                tipo_pago_id=5, status_trans_id=1).values("id", "cuenta_emisor", "nombre_emisor",
                                        "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                                        "concepto_pago", "tipo_pago__nombre_tipo",
                                        "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                                        "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor",
                                        "referencia_numerica", "email")

        else:
            #print("IF Filter True")
            if data["account_receiver"] != None and str(data["account_receiver"]) != "null" and str(
                data["account_receiver"]) != "false":
                dataFilter["cta_beneficiario"] = data["account_receiver"]
            if data["operation_date"] != None and str(data["operation_date"]) != "null" and str(
                data["operation_date"]) != "false":
                dataFilter["fecha_creacion"] = data["operation_date"]
            if data["date_start"] != None and str(data["date_start"]) != "null" and str(
                data["date_start"]) != "false":
                dataFilter["fecha_creacion__date__gte"] = data["date_start"]
            if data["date_end"] != None and str(data["date_end"]) != "null" and str(
                data["date_end"]) != "false":
                dataFilter["fecha_creacion__date__lte"] = data["date_end"]

            # Enviadas
            if data["payment_type"] == 1:
                queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                Q(status_trans_id=1) | Q(status_trans_id=3), tipo_pago_id=1, **dataFilter).values("id", "cuenta_emisor", "nombre_emisor",
                "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                "concepto_pago", "tipo_pago__nombre_tipo",
                "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica","email")

            # Recibidas
            elif data["payment_type"] == 8:
                queryMovimientos = transferencia.objects.filter(
                    Q(cta_beneficiario=queryCuentaCLABE[0]["cuenta"]) | Q(cta_beneficiario=queryCuentaCLABE[0]["cuentaclave"]),
                    tipo_pago_id=5, status_trans_id=1, **dataFilter).values("id", "cuenta_emisor", "nombre_emisor",
                    "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                    "concepto_pago", "tipo_pago__nombre_tipo",
                    "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                    "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica","email")

        #print("cuenta["+str(queryCuentaCLABE[0]["cuenta"])+"] clabe["+str(queryCuentaCLABE[0]["cuentaclave"])+"]")
        #print(queryMovimientos)

        return queryMovimientos



    def _buildCsvContent(self, headers, queryMovimientos):
        contenido_csv = headers
        for m in queryMovimientos:
            # print(m)
            empresa_emisor = m["nombre_emisor"]
            empresa_destino = m["nombre_beneficiario"]

            if m["emisor_empresa__name"] == None:
                m["emisor_empresa__name"] = "SinNombre"

            if m["emisor_empresa__last_name"] == None:
                m["emisor_empresa__last_name"] = "SinApellidos"

            if m["masivo_trans_id"] == None:
                m["masivo_trans_id"] = "Individual"
            else:
                m["masivo_trans_id"] = "Masiva"

            nombre_colaborador = m["emisor_empresa__name"] + m["emisor_empresa__last_name"]

            contenido_csv = contenido_csv + str(m["clave_rastreo"]) + ";" + str(m["nombre_beneficiario"]) + ";" + \
                str(m["cta_beneficiario"]) + ";" + str(m["receiving_bank__institucion"]) + ";" + \
                str(m["cuenta_emisor"]) + ";" + str(m["nombre_emisor"]) + ";" + str(m["rfc_curp_emisor"]) + ";" + \
                str(m["monto"]) + ";" + str(m["concepto_pago"]) + ";" + str(m["referencia_numerica"]) + ";" + \
                str(m["fecha_creacion"]) + ";" + str(m["tipo_pago__nombre_tipo"]) + ";" + \
                str(m["masivo_trans_id"]) + ";" + str(m["email"]) + "\n"

        # Se almacena contenido en archivo temporal
        with open(self.tmpName, "wb") as file1:
            ftmp = File(file1)
            ftmp.write(contenido_csv.encode("utf-8"))
        ftmp.close()
        file1.close()

        return self.tmpName



    def _loadFileToAWS(self, path_nombreTmpCSV):
        # (ChrGil 2021-12-07) Metodo para crear un documento
        """
        def create_document(self, tipo: int, owner: int, comment: Union[str, None]):
            document = self.model(tdocumento_id=tipo, person_id=owner, comentario=comment)
            document.save(using=self._db)
            return document
        """
        #print("path_nombreTmpCSV["+str(path_nombreTmpCSV)+"]")

        documentCSV = documentos.objects.create_document(
            comment="Export CSV",
            owner=self.request.user.id,
            tipo=22
        )
        with open(path_nombreTmpCSV, "rb") as file2:
            atmp2 = File(file2)
            documentCSV.documento = atmp2
            documentCSV.save()
        atmp2.close()
        file2.close()

        # Se elimina CSV local (temporal)
        remove(path_nombreTmpCSV)
        #print("awsPATH["+str(documentCSV.get_url_aws_document())+"]")
        return documentCSV.get_url_aws_document()



    def export(self):
        #print("export self.type["+str(self.type)+"]")
        #print("export self.tmpPath[" + str(self.tmpPath) + "]")
        #print("export self.tmpName[" + str(self.tmpName) + "]")
        #print("export self.csvStructure[" + str(self.csvStructure) + "]")
        #print("export self.data[" + str(self.data) + "]")
        #print("export self.request[" + str(self.request) + "]")

        queryMovimientos    = self._getData(self.data)
        if type(queryMovimientos ) == dict:
            if int(queryMovimientos ["code"][0]) == 400:
                return queryMovimientos
        self._buildCsvContent(self.csvStructure, queryMovimientos)
        awsPath             =self._loadFileToAWS(self.tmpName)
        #print("aws["+str(awsPath)+"]")

        return awsPath