# -*- coding: utf-8 -*-
import subprocess

from typing import ClassVar

import firebase_admin
from decouple import config
from pathlib import Path
import os

from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'o%#0c#&0_5yfjn387!+bky8i!lt+=dtmoz7-^=man$vpl-atfp'

DEBUG = True

ALLOWED_HOSTS = ['*']

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 8,
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.users.authorization.ExpiringTokenAuthentication',
    ),
}

BASE_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'apps.transaction.apps.TransactionConfig',
    'apps.reportes.apps.ReportesConfig',
    'apps.users.apps.UsersConfig',
    'apps.contacts',
    'apps.solicitudes',
    'apps.gadgets',
    'apps.productos',
    'apps.permision',
    'apps.api_client',
    'apps.notifications',
    'apps.languages',
    'apps.api_dynamic_token',
    'apps.api_stp',
    'apps.logspolipay',
    'apps.suppliers',
    'apps.commissions',
    'apps.services_pay',
    'apps.paycash',
]

THIRD_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'storages',
]

INSTALLED_APPS = BASE_APPS + LOCAL_APPS + THIRD_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'polipaynewConfig.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'TEMPLATES/emails')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'polipaynewConfig.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'walletpruebas',
        'USER': 'admin',
        'PASSWORD': 'P0l1M3NT3S#bdd__p0l1p4ypru3b4s#P0l1m3nt3s2022.',
        'HOST': 'tester.cjwjlfxbub8a.us-east-1.rds.amazonaws.com',
        'PORT': '3306',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'pre_spp',
#         'USER': 'admin',
#         'PASSWORD': 'P0l1M3NT3S#bdd__p0l1p4ypru3b4s#P0l1m3nt3s2022.',
#         'HOST': 'tester.cjwjlfxbub8a.us-east-1.rds.amazonaws.com',
#         'PORT': '3306',
#     }
# }

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.mysql',
#        'NAME': 'spp',
#        'USER': 'admin',
#        'PASSWORD': 'P0l1M3NT3S#bdd__p0l1p4y#P0l1m3nt3s2022.',
#        'HOST': 'stagepolipay.cjwjlfxbub8a.us-east-1.rds.amazonaws.com',
#        'PORT': '3306',
#    }
# }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# 30 minutos de duracion
TOKEN_EXPIRED_AFTER_SECONDS = 1800

# Por fines productivos y de pruebas se aumento el tiempo de expiración del token a 60 dias
# TOKEN_EXPIRED_AFTER_SECONDS = 5184000

CORS_ORIGIN_ALLOW_ALL = True
CORS_ORIGIN_WHITELIST = []

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# custom user
AUTH_USER_MODEL = 'users.persona'

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'noreply@polipay.mx'
EMAIL_HOST_PASSWORD = 'Temporal123'
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = 'noreply@polipay.mx'

"""
EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST = 'smtp-relay.gmail.com'
# EMAIL_HOST_USER = 'cavalosb.p0l1m3nt3s.tester@gmail.com'
# EMAIL_HOST_PASSWORD = 'P0l1m3nt3s.123'
# EMAIL_USE_TLS = True
# EMAIL_PORT = 587
EMAIL_USE_SSL = True
EMAIL_PORT = 465
DEFAULT_FROM_EMAIL = 'cavalosb.p0l1m3nt3s.tester@gmail.com'
"""

# Email para noreply C.
EMAIL_USER_NC = 'noreply.competitividad21@gmail.com'
EMAIL_PASSWORD_NC = '248264684004003a1'
EMAIL_NC_TO = "direccion@competitividad21.com"

# AWS_STORAGE BUCKETS SETTINGS

AWS_ACCESS_KEY_ID = 'AKIA52NUTQQOITIV7FVN'
AWS_SECRET_ACCESS_KEY = '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'
# AWS_ACCESS_KEY_ID = 'AKIA52NUTQQOAS4T2DMJ'
# AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = 'polipayimage'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# ----------------------Bucket pruebas ----------------------------------
# AWS_ACCESS_KEY_ID = 'AKIA52NUTQQOAS4T2DMJ'
# AWS_SECRET_ACCESS_KEY = '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'
# AWS_STORAGE_BUCKET_NAME = 'polipaybancap'

# ----------------------Bucket produccion----------------------------------
# AWS_ACCESS_KEY_ID = 'AKIA52NUTQQOAS4T2DMJ'
# AWS_SECRET_ACCESS_KEY = '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'
# AWS_STORAGE_BUCKET_NAME = 'polipaybanca'


STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'polipaynewConfig'),
]

AWS_LOCATION = 'static'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'polipaynewConfig.storage_backends.MediaStorage'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
    }
}

##INNTEC CONFIG
# Test
URL_POLIPAY_Test = "http://desarrolloinntecmp.azurewebsites.net/InntecAPI/"
CLIENT_ID_Test = "C000022"
CLIENT_SECRET_Test = "114AD4DE-36D6-458A-86F7-9660193C65A9"
USERNAME_Test = "demo_api_polimentes"
PASSWORD_Test = "wevjh7923ujbdv78923"

## INNTEC CONFIG
# production
URL_POLIPAY = "https://www.inntecmp.com.mx/InntecAPI/"
CLIENT_ID = "C000682"
CLIENT_SECRET = "47FF1C09-617E-4AB3-BF8D-583488D4CECA"
USERNAME = "Polimentes_"
PASSWORD = "f0dR60QXExGHmxIx2Bcx"

# script = Path('MANAGEMENT/TaskPlanner/Dispersions/dispersion.py')
# COMMAND_CRONTAB = f'/home/chris/Documents/polimentes/wallet/polipaynew/venv/bin/python {script.resolve()}\t'

# Twilio config
account_sid = 'ACe137e3186ee303e0a9c950af463693eb'
auth_token = '37957a245d246cdce41eed66db868cda'
phone_twilio = '+12054967349'

# Id de los permisos
Admin = 108
SuperAdmin = 10
AdministrativoPolipayDispersa = 6
AdministrativoPolipayEmpresa = 7
AdministrativoPolipayLiberate = 8
COLABORADOR_DISPERSA = 128
COLABORADOR_EMPRESA = 129
CLIENTE_EXTERNO = 36
GRUPO_BRIGADISTA = 113
BeneficiarioDispersa = 114

# Lista de id de permisos de colaborador dispersa
# colaborador_dispersa = [244, 365, 245, 246, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296,
#                         297, 298, 299, 301, 304, 306, 307, 308, 309, 310, 311, 318, 319, 320, 327, 328, 329, 330, 331,
#                         332, 333]


# Constantes
ADMIN_DISPERSA = 6
ADMIN_EMPRESA = 7
ADMIN_LIBERATE = 8

PASS_FRONTEND: bytes = config('PASS_FRONTEND').encode('utf-8')
IV_FRONTEND: bytes = config('IV_FRONTEND').encode('utf-8')

PASS_MOBILE: bytes = config('PASS_MOBILE').encode('utf-8')
IV_MOBILE: bytes = config('IV_MOBILE').encode('utf-8')
PUB_KEY_MOBILE = config('PUB_KEY_MOBILE').encode('utf-8')

# (ChrGil 2022-03-24) Access keys Pruebas
PRIVATE_KEY_STP: str = config('PRIVATE_KEY_STP')
PUBLIC_KEY_STP_CER: str = config('PUBLIC_KEY_STP_CER')
PASS_STP_PRIVATE_KEY: bytes = config('PASS_STP_PRIVATE_KEY').encode('utf-8')

# (ChrGil 2022-03-24) Access keys producción STP
PRIVATE_KEY_STP_PRODUCTION: str = config('PRIVATE_KEY_STP_PRODUCTION')
PUBLIC_KEY_STP_CER_PRODUCTION: str = config('PUBLIC_KEY_STP_CER_PRODUCTION')
PASS_STP_PRIVATE_KEY_PRODUCTION: bytes = config('PASS_STP_PRIVATE_KEY_PRODUCTION').encode('utf-8')
PARAPHRASE: ClassVar[bytes] = config('PARAPHRASE').encode('utf-8')

# (ChrGil 2022-01-21) Se deja parametrizado el RFC de GRUPOBEC para INNTEC
rfc_Bec = "BECX161026BX3"

# RS_POLIPAY_COMISSION = config('RS_POLIPAY_COMISSION_TEST')
# (AAF 2022-01-31) variables para Concentrados
TINGRESOSC = 0
TEGRESOSC = 0

# CENTRO DE COSTOS COMISIONES [TESTER]
COST_CENTER_POLIPAY_COMISSION: int = 79
CLABE_POLIPAY_COMISSION: str = "646180171802500018"
COST_CENTER_POLIPAY_PAYCASH_COMISSION: int = 2349

# CENTRO DE COSTOS COMISIONES [PRELAUNCH | STAGE]
# COST_CENTER_POLIPAY_COMISSION: int = 1855
# CLABE_POLIPAY_COMISSION: str = "646180171802500018"
# COST_CENTER_POLIPAY_PAYCASH_COMISSION: int = 2349

# CENTRO DE COSTOS INFORMATIVO INNTEC [PRELAUNCH]
COST_CENTER_INNTEC: int = 2114
# CENTRO DE COSTOS INFORMATIVO INNTEC [STAGE]
# COST_CENTER_INNTEC: int = 2086

# ------ Configuracion STP ------
# STP INTEGRACIÓN [TESTER]
HOST_STP = "https://demo.stpmex.com:7024"
HOST_STP_CONSULTA_SALDO = "https://efws-dev.stpmex.com"

# STP INTEGRACIÓN [STAGE]
# HOST_STP = "https://prod.stpmex.com:7002"


# ------ Configuracion RED EFECTIVA ------
# INTEGRACIÓN RED EFECTIVA [TESTER]
SOAP_HOST_RED_EFECTIVA = "https://sandbox-txservice.redefectiva.net/WSCertificacion/server.asmx?WSDL"
CORRESPONSAL = 438
S_CAJA = "SandBox06"
S_CODIGO = "MQ4DE78H"
COMERCIO = 1
S_SUCURSAL = ""

# INTEGRACIÓN RED EFECTIVA [STAGE]
# SOAP_HOST_RED_EFECTIVA = ""
# CORRESPONSAL = 0
# S_CAJA = ""
# S_CODIGO = ""
# COMERCIO = 1
# S_SUCURSAL = ""


PREFIX_STP_BECPOLIMENTES = '1718'

# INTEGRACIÓN PAYCASH
KEY_PAYCASH: str = config('KEY_PAYCASH')
HOST_PAYCASH: str = "https://sb-api-mexico-emisor.paycashglobal.com"
