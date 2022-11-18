from os import remove
from datetime import datetime

from django.db.models import Q
from django.core.files import File

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.settings import api_settings

from apps.permision.permisions import BlocklistPermissionV2
from apps.transaction.api.web.serializers.serializers_transaction_export_file import *
from apps.users.models import persona, cuenta, documentos
from apps.transaction.models import transferencia
from MANAGEMENT.ExportCSV.Dispersions import *
from MANAGEMENT.ExportCSV.TransactionsPolipayToPolipay import *
from MANAGEMENT.ExportCSV.TransactionsPolipayToTerceros import *
from MANAGEMENT.ExportCSV.TransactionsCuentasPropias import *



class GenerateDataExportToCsv():

    # CASO 01 - Transacciones Polipay a Polipay
    # CASO 02 - Transacciones Polipay a terceros
    # CASO 03 - Transacciones Cuentas propias
    # CASO 04 - Dispersiones

    def __init__(self, type=0, tmpPath="", tmpName="", awsPath="", csvStructure="", data=None, request=None):
        self.type           = type
        self.tmpPath        = tmpPath
        self.tmpName        = tmpName
        self.awsPath        = awsPath
        self.csvStructure   = csvStructure
        self.data           = data
        self.request        = request

    def getRealAwsPath(self):
        value = getattr(self, 'documento', api_settings.UPLOADED_FILES_USE_URL)
        return value.url

    def createCsv(self):
        #print("createCsv self.type["+str(self.type)+"]")

        if int(self.type) == 1:
            #print("En self.type["+str(self.type)+"]")
            objExpCsv1          = TransactionsPolipayToPolipay(
                type            = self.type,
                tmpPath         = self.tmpPath,
                tmpName         = self.tmpName,
                csvStructure    = self.csvStructure,
                data            = self.data,
                request         = self.request
            )
            r   = objExpCsv1.export()
            #print("r["+str(r)+"]")
            if type(r) == dict:
                if int(r["code"][0]) == 400:
                    return r
            else:
                self.awsPath    = r


        elif int(self.type) == 2:
            objExpCsv2 = TransactionsPolipayToTerceros(
                type            = self.type,
                tmpPath         = self.tmpPath,
                tmpName         = self.tmpName,
                csvStructure    = self.csvStructure,
                data            = self.data,
                request         = self.request
            )
            r = objExpCsv2.export()
            if type(r) == dict and int(r["code"][0]) == 400:
                return r
            else:
                self.awsPath = r


        elif int(self.type) == 3:
            objExpCsv3 = TransactionsCuentasPropias(
                type            = self.type,
                tmpPath         = self.tmpPath,
                tmpName         = self.tmpName,
                csvStructure    = self.csvStructure,
                data            = self.data,
                request         = self.request
            )
            r = objExpCsv3.export()
            if type(r) == dict and int(r["code"][0]) == 400:
                return r
            else:
                self.awsPath = r


        elif int(self.type) == 4:
            objExpCsv4 = Dispersions(
                type            = self.type,
                tmpPath         = self.tmpPath,
                tmpName         = self.tmpName,
                csvStructure    = self.csvStructure,
                data            = self.data,
                request         = self.request
            )
            r = objExpCsv4.export()
            if type(r) == dict and int(r["code"][0]) == 400:
                return r
            else:
                self.awsPath = r

        else:
            pass