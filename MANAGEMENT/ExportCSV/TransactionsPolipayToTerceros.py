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

# CASO 02 - Transacciones Polipay a terceros

class TransactionsPolipayToTerceros():

    def __init__(self, type=0, tmpPath="", tmpName="", csvStructure="", data=None, request=None):
        self.type           = type
        self.tmpPath        = tmpPath
        self.tmpName        = tmpName
        self.csvStructure   = csvStructure
        self.data           = data
        self.request        = request



    def _validateEmp(self, company_id):
        queryExisteEmpresa = persona.objects.filter(id=int(company_id)).exists()
        if not queryExisteEmpresa:
            r = {
                "code": [400],
                "status": "OK",
                "detail": [
                    {
                        "field": "company_id",
                        "data": str(company_id),
                        "message": "No existe la empresa."
                    }
                ]
            }
            return r

    def _getData(self):
        queryMovimientos = None

        # Cofirmo que existe empres
        self._validateEmp(data["company_id"])

        # Recupero cuenta y clabe de la empresa
        queryCuentaCLABE = cuenta.objects.filter(persona_cuenta_id=int(data["company_id"])).values("id", "cuenta",
                                                                                                   "cuentaclave")

        # Recupero movimientos
        dataFilter = {}

        if data["filter"] == None or str(data["filter"]) == "null" or str(data["filter"]) == "false":
            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                tipo_pago_id=7).values("id", "cuenta_emisor", "nombre_emisor",
                                       "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                                       "concepto_pago", "tipo_pago__nombre_tipo",
                                       "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                                       "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica", "email")
        else:
            if data["transaction_id"] != None and str(data["transaction_id"]) != "null" and str(
                data["transaction_id"]) != "false":
                dataFilter["id"] = data["transaction_id"]
            if data["account_transmitter"] != None and str(data["account_transmitter"]) != "null" and str(
                data["account_transmitter"]) != "false":
                dataFilter["cuenta_emisor"] = data["account_transmitter"]
            if data["account_receiver"] != None and str(data["account_receiver"]) != "null" and str(
                data["account_receiver"]) != "false":
                dataFilter["cta_beneficiario"] = data["account_receiver"]
            if data["amount"] != None and str(data["amount"]) != "null" and str(data["amount"]) != "false":
                dataFilter["monto"] = data["amount"]
            if data["operation_date"] != None and str(data["operation_date"]) != "null" and str(
                data["operation_date"]) != "false":
                dataFilter["fecha_creacion"] = data["operation_date"]

            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                tipo_pago_id=7, **dataFilter).values("id", "cuenta_emisor", "nombre_emisor",
                                                     "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                                                     "concepto_pago", "tipo_pago__nombre_tipo",
                                                     "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                                                     "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica",
                                                     "email")

        return queryMovimientos



    def _buildCsvContent(self, headers, queryMovimientos, caseNum):
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

            if caseNum == 1:
                contenido_csv = contenido_csv + str(m["id"]) + ";" + str(empresa_destino) + ";" + str(
                    m["cta_beneficiario"]) + ";" + str(empresa_emisor) + ";" + str(m["cuenta_emisor"]) + ";" + str(
                    m["monto"]) + ";" + str(m["concepto_pago"]) + ";" + str(m["fecha_creacion"]) + ";" + str(
                    m["tipo_pago__nombre_tipo"]) + ";" + str(nombre_colaborador) + "\n"

            elif caseNum == 2:
                contenido_csv = contenido_csv + str(m["clave_rastreo"]) + ";" + str(m["nombre_beneficiario"]) + ";" + \
                                str(m["cta_beneficiario"]) + ";" + str(m["receiving_bank__institucion"]) + ";" + \
                                str(m["cuenta_emisor"]) + ";" + str(m["nombre_emisor"]) + ";" + str(m["rfc_curp_emisor"]) + ";" + \
                                str(m["monto"]) + ";" + str(m["concepto_pago"]) + ";" + str(m["referencia_numerica"]) + ";" + \
                                str(m["fecha_creacion"]) + ";" + str(m["tipo_pago__nombre_tipo"]) + ";" + \
                                str(m["masivo_trans_id"]) + ";" + str(m["email"]) + "\n"

        # Se almacena contenido en archivo temporal
        fhNow = datetime.now()
        fh = fhNow.strftime("%Y%m%d%H%m%S%s")
        nombreTmpCSV = "UID" + str(self.request.user.id) + "T" + str(fh) + ".csv"
        path_nombreTmpCSV = "TMP/ExportCSV/" + str(nombreTmpCSV)
        with open(path_nombreTmpCSV, "wb") as file1:
            ftmp = File(file1)
            ftmp.write(contenido_csv.encode("utf-8"))
        ftmp.close()
        file1.close()

        return path_nombreTmpCSV



    def _loadFileToAWS(self, path_nombreTmpCSV):
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

        return documentCSV



    def export(self):
        queryMovimientos = self._getData(self.data)
        self._buildCsvContent(self.csvStructure, queryMovimientos)
        self._loadFileToAWS(self.tmpName)