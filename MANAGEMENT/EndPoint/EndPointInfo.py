import json
from datetime import datetime

from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status

def get_info(request):
    ep  = str(request.scheme) + "://" + str(request.get_host()) + str(request.path)
    return ep

def get_scheme(request):
    return str(request.scheme)

def get_host(request):
    return str(request.get_host())

def get_path(request):
    return str(request.path)