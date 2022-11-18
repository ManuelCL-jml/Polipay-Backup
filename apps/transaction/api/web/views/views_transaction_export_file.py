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
from MANAGEMENT.ExportCSV.GenerateDataExportToCsv import *



class ExportDataToCSV(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Crear Administrador", "Ver Administradores", "Editar Administrador", "Eliminar Administrador"]
    #serializer_class    =
    #permission_classes  = [IsAuthenticated]
    permission_classes = ()



    def getMovements(self, data, request):
        r   = {}
        tmpPath = "TMP/ExportCSV/"

        # CASO 01 - Transacciones Polipay a Polipay
        if int(data["type"]) == 1:
            print("CASO 01 - Transacciones Polipay a Polipay")
            # Contenido del CSV
            headers = "clabe_rastreo;nombre_beneficiario;cuenta_destino;banco_destino;cuenta_origen;ordenante;"
            headers = headers + "rfc_ordenante;monto;concepto;referencia;fecha_operacion;tipo_operacion;origen;correo_electronico_destinatario\n"

            objExportarCsvC1    = GenerateDataExportToCsv(
                type            = 1,
                tmpPath         = tmpPath,
                awsPath         = tmpPath,
                csvStructure    = headers,
                data            = data,
                request         = request
            )
            pathAwsFile = objExportarCsvC1.createCsv()
            if type(pathAwsFile) == dict:
                if int(pathAwsFile["code"][0]) == 400:
                    r   = pathAwsFile
            else:
                r = {
                    "code": [200],
                    "csv": str(objExportarCsvC1.awsPath)
                }


        # CASO 02 - Transacciones Polipay a terceros
        elif int(data["type"]) == 2:
            print("CASO 02 - Transacciones Polipay a terceros")
            # Contenido del CSV
            headers = ""

            objExportarCsvC2 = GenerateDataExportToCsv(
                type            = 2,
                tmpPath         = tmpPath,
                awsPath         = tmpPath,
                csvStructure    = headers,
                data            = data,
                request         = request
            )
            pathAwsFile = objExportarCsvC2.createCsv()
            if type(pathAwsFile) == dict:
                if int(pathAwsFile["code"][0]) == 400:
                    r = pathAwsFile
            else:
                r = {
                    "code": [200],
                    "csv": str(objExportarCsvC2.awsPath)
                }


        # CASO 03 - Transacciones Cuentas propias
        elif int(data["type"]) == 3:
            print("CASO 03 - Transacciones Cuentas propias")
            # Contenido del CSV
            headers = "id;empresa_destino;cuenta_destino;empresa_origen;cuenta_origen;monto;concepto;fecha_operacion;tipo_operacion;colaborador_realiza_operacion\n"

            objExportarCsvC3 = GenerateDataExportToCsv(
                type            = 3,
                tmpPath         = tmpPath,
                awsPath         = tmpPath,
                csvStructure    = headers,
                data            = data,
                request         = request
            )
            pathAwsFile = objExportarCsvC3.createCsv()
            if type(pathAwsFile) == dict:
                if int(pathAwsFile["code"][0]) == 400:
                    r = pathAwsFile
            else:
                r = {
                    "code": [200],
                    "csv": str(objExportarCsvC3.awsPath)
                }


        # CASO 04 - Dispersiones
        elif int(data["type"]) == 4:
            print("CASO 04 - Dispersiones")
            # Contenido del CSV
            headers = ""

            objExportarCsvC4 = GenerateDataExportToCsv(
                type            = 4,
                tmpPath         = tmpPath,
                awsPath         = tmpPath,
                csvStructure    = headers,
                data            = data,
                request         = request
            )
            pathAwsFile = objExportarCsvC4.createCsv()
            if type(pathAwsFile) == dict:
                if int(pathAwsFile["code"][0]) == 400:
                    r = pathAwsFile
            else:
                r = {
                    "code": [200],
                    "csv": str(objExportarCsvC4.awsPath)
                }


        else:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "type",
                        "data": data["type"],
                        "message": "Valor para type incorrecto."
                    }
                ]
            }

        return r


    def list(self, request):
        r = {}
        objJson = {}

        # Realizo querySet del escenario
        r   = self.getMovements(data=self.request.query_params, request=request)

        if int(r["code"][0]) == 400:
            return Response(r, status=status.HTTP_400_BAD_REQUEST)
        else:
            r = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "field": "Archivo",
                        "data": r["csv"],
                        "message": "Creación correcta de CSV."
                    }
                ]
            }
            return Response(r, status=status.HTTP_200_OK)



class ExportDataToCSV_2_BORRAR(ListAPIView):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Crear Administrador", "Ver Administradores", "Editar Administrador", "Eliminar Administrador"]
    #serializer_class    =
    #permission_classes  = [IsAuthenticated]
    permission_classes = ()

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

    def _getDataCase1(self, data):
        queryMovimientos    = None

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
                "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica", "email")

        return queryMovimientos

    def _getDataCase2(self, data):
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
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"])
                ).values("id", "cuenta_emisor", "nombre_emisor",
                "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                "concepto_pago", "tipo_pago__nombre_tipo",
                "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica", "email")
        else:
            if data["operation_date"] != None and str(data["operation_date"]) != "null" and str(
                data["operation_date"]) != "false":
                dataFilter["fecha_creacion"] = data["operation_date"]
            else:

                if data["date_start"] != None and str(data["date_start"]) != "null" and str(data["date_start"]) != "false":
                    dataFilter["fecha_creacion__date__gte"] = data["date_start"]

                if data["date_end"] != None and str(data["date_end"]) != "null" and str(data["date_end"]) != "false":
                    dataFilter["fecha_creacion__date__lte"] = data["date_end"]

            queryMovimientos = transferencia.objects.filter(
                Q(cuenta_emisor=queryCuentaCLABE[0]["cuenta"]) | Q(cuenta_emisor=queryCuentaCLABE[0]["cuentaclave"]),
                **dataFilter).values("id", "cuenta_emisor", "nombre_emisor",
                "cta_beneficiario", "nombre_beneficiario", "monto", "fecha_creacion",
                "concepto_pago", "tipo_pago__nombre_tipo",
                "emisor_empresa__name", "emisor_empresa__last_name", "masivo_trans_id",
                "clave_rastreo", "receiving_bank__institucion", "rfc_curp_emisor", "referencia_numerica", "email")

        return queryMovimientos

    def _getDataCase3(self, data):
        pass

    def _getDataCase4(self, data):
        pass

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
                m["masivo_trans_id"]    = "Individual"
            else:
                m["masivo_trans_id"]    = "Masiva"

            nombre_colaborador = m["emisor_empresa__name"] + m["emisor_empresa__last_name"]


            if caseNum == 1:
                contenido_csv = contenido_csv + str(m["id"]) + ";" + str(empresa_destino) + ";" + str(
                m["cta_beneficiario"]) + ";" + str(empresa_emisor) + ";" + str(m["cuenta_emisor"]) + ";" + str(
                m["monto"]) + ";" + str(m["concepto_pago"]) + ";" + str(m["fecha_creacion"]) + ";" + str(
                m["tipo_pago__nombre_tipo"]) + ";" + str(nombre_colaborador) + "\n"

            elif caseNum == 2:
                contenido_csv = contenido_csv + str(m["clave_rastreo"]) + ";" + str(m["nombre_beneficiario"]) + ";" +\
                    str(m["cta_beneficiario"]) + ";" + str(m["receiving_bank__institucion"]) + ";" +\
                    str(m["cuenta_emisor"]) + ";" + str(m["nombre_emisor"]) + ";" + str(m["rfc_curp_emisor"]) + ";" +\
                    str(m["monto"]) + ";" + str(m["concepto_pago"]) + ";" + str(m["referencia_numerica"]) + ";" +\
                    str(m["fecha_creacion"]) + ";" + str(m["tipo_pago__nombre_tipo"]) + ";" +\
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

    def getMovements(self, data):
        r   = None

        # Caso 1: Tranacciones / Cuentas propias / Historial de transferencias (https://app.zeplin.io/project/603d29e07ecd6919cd498e3a/screen/60be9687dfa5a7177dd50c44)
        if int(data["type"]) == 1:
            # Recupera movimientos
            queryMovimientos    = self._getDataCase1(data)

            # Contenido del CSV
            headers             = "id;empresa_destino;cuenta_destino;empresa_origen;cuenta_origen;monto;concepto;fecha_operacion;tipo_operacion;colaborador_realiza_operacion\n"
            path_nombreTmpCSV   = self._buildCsvContent(headers, queryMovimientos, 1)

            # Se sube CSV a AWS
            documentCSV = self._loadFileToAWS(path_nombreTmpCSV)

            r = {
                "code": [200],
                "csv": str(documentCSV.get_url_aws_document())
            }



        # Caso 2: Todos (https://app.zeplin.io/project/603d29e07ecd6919cd498e3a/screen/606b5fb86f62d9804ceb99da)
        elif int(data["type"]) == 2:
            # Recupera movimientos
            queryMovimientos = self._getDataCase2(data)

            # Contenido del CSV
            headers = "clabe_rastreo;nombre_beneficiario;cuenta_destino;banco_destino;cuenta_origen;ordenante;"
            headers = headers + "rfc_ordenante;monto;concepto;referencia;fecha_operacion;tipo_operacion;origen;correo_electronico_destinatario\n"
            path_nombreTmpCSV = self._buildCsvContent(headers, queryMovimientos, 2)

            # Se sube CSV a AWS
            documentCSV = self._loadFileToAWS(path_nombreTmpCSV)

            r = {
                "code": [200],
                "csv": str(documentCSV.get_url_aws_document())
            }



        # Caso 3: Transacciones / Polipay a polipay ENVIADAS (https://app.zeplin.io/project/603d29e07ecd6919cd498e3a/screen/60400954e3c2aea696ed8eeb)
        elif int(data["type"]) == 3:
            pass



        # Caso 4: Transacciones / Polipay a polipay RECIBIDAS (https://app.zeplin.io/project/603d29e07ecd6919cd498e3a/screen/60400954e3c2aea696ed8eeb)
        elif int(data["type"]) == 4:
            pass



        else:
            r = {
                "code": [400],
                "status": "ERROR",
                "detail": [
                    {
                        "field": "type",
                        "data": data["type"],
                        "message": "Valor para type incorrecto."
                    }
                ]
            }

        return r


    def list(self, request):
        r = {}
        objJson = {}

        # Realizo querySet del escenario
        r   = self.getMovements(data=self.request.query_params)

        if int(r["code"][0]) == 400:
            return Response(r, status=status.HTTP_400_BAD_REQUEST)
        else:
            r = {
                "code": [200],
                "status": "OK",
                "detail": [
                    {
                        "field": "Archivo",
                        "data": r["csv"],
                        "message": "Creación correcta de CSV."
                    }
                ]
            }
            return Response(r, status=status.HTTP_200_OK)