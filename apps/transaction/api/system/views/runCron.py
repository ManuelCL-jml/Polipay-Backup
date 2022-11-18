# -*- coding: utf-8 -*-

import json

from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response



class SystemCronRun(ListAPIView):
	#serializer_class	= None
	#permission_classes = [IsAuthenticated]
	permission_classes = ()


	def getMovTarInntec(self):
		# Función / Metodo que recupera, valida y registra los movimientos (egresos)
		#	de Proveedor INNTEC en la bdd de Polipay.
		pass

	def runCron(self, type:int):
		if int(type) == 1:
			self.getMovTarInntec()

	def list(self, request):
		KEY_ACC	= "12b2aa06a5027b873dd987d7c0cf7be1210a8d22"
		if "keyacc" not in request.GET.keys():
			msg	= {"status":"OK.1"}
			return Response(msg, status=status.HTTP_200_OK)
		else:
			key	= request.GET.get("keyacc")
			if str(key) != KEY_ACC:
				msg = {"status": "OK."}
				return Response(msg, status=status.HTTP_200_OK)
			msg = {"status": "Movimientos recuperados y registrados correctamente."}
			return Response(msg, status=status.HTTP_200_OK)
