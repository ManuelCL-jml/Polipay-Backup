# Modulos nativos
from django.contrib.auth.models import Group

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.logspolipay.manager import RegisterLog
from polipaynewConfig.settings import Admin, SuperAdmin, BeneficiarioDispersa, AdministrativoPolipayDispersa, \
    AdministrativoPolipayLiberate, AdministrativoPolipayEmpresa, COLABORADOR_DISPERSA, CLIENTE_EXTERNO, \
    COLABORADOR_EMPRESA

from apps.users.models import grupoPersona, cuenta, persona
from MANAGEMENT.Standard.errors_responses import MyHttpError


class BlocklistPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        user_log = request.user.groups.all().values("name")
        if request.user == "AnonymousUser" or None:
            raise PermissionDenied({"status": "Usuario no autorizado"})
        grupo_security, created = Group.objects.get_or_create(name=user_log[0]['name'])
        permissionsGroup = grupo_security.permissions.all().values('codename')
        for permision in permissionsGroup:
            if permision['codename'] in view.permisos:
                if request.method == "GET":
                    if "get" in permision["codename"].split("_"):
                        return True
                if request.method == "POST":
                    if "create" in permision["codename"].split("_"):
                        return True
                if request.method == "PUT":
                    if "edit" in permision["codename"].split("_"):
                        return True
        raise PermissionDenied({"status": "Usuario no autorizado"})


###########################################################################

class BlocklistPermissionV2(permissions.BasePermission):

    def has_permission(self, request, view):
        # log = RegisterLog(request.user, request)

        if request.user == "AnonymousUser" or None:
            err = MyHttpError('Usted no tiene permiso para acceder a este sitio', real_error=None)
            raise PermissionDenied(err.standard_error_responses())

        user_log = request.user.groups.all().values("name")

        if not user_log:
            err = MyHttpError('Usted no tiene permiso para acceder a este sitio', real_error=None)
            # log.json_response(err.standard_error_responses())
            raise PermissionDenied(err.standard_error_responses())

        # Hacer una condicion para ver si tiene un grupo de permiso
        if user_log[0]['name'] == None or user_log[0]['name'] == '':

            # - Ver si es admin y super admin para dar los permisos de super admin
            if request.user.is_superuser == True and request.user.is_staff == True:
                query_group = Group.objects.get(id=SuperAdmin)

            # - Si solo tiene admin dar los permisos para admin
            if request.user.is_superuser == False and request.user.is_staff == True:
                query_group = Group.objects.get(id=Admin)
            # - Ver si es un administrativo de cuenta
            type_admin = grupoPersona.objects.filter(person_id=request.user.id, relacion_grupo_id__in=[1, 3],
                                                     is_admin=True).values('empresa_id')

            if type_admin:
                # Identificar a que producto pertenece el usuario

                #   Polipay. Dispersa.
                queryProduvto = cuenta.objects.get(persona_cuenta_id=type_admin[0]['empresa_id'])
                if queryProduvto.rel_cuenta_prod_id == 1:
                    query_group = Group.objects.get(id=AdministrativoPolipayDispersa)

                #   Polipay. Liberate
                if queryProduvto.rel_cuenta_prod_id == 2:
                    query_group = Group.objects.get(id=AdministrativoPolipayLiberate)

                #   Polipay. Empresa
                if queryProduvto.rel_cuenta_prod_id == 3:
                    query_group = Group.objects.get(id=AdministrativoPolipayEmpresa)

            # - Ver si es un colaborador dispersa o empresa
            type_colaborator = grupoPersona.objects.filter(person_id=request.user.id, relacion_grupo_id=[8,14]).values('empresa_id')

            if type_colaborator:
                query_producto = cuenta.objects.get(persona_cuenta_id=type_colaborator[0]['empresa_id'])

                if query_producto.rel_cuenta_prod_id == 1:
                    query_group = Group.objects.get(id=COLABORADOR_DISPERSA)

                if query_producto.rel_cuenta_prod_id == 3:
                    query_group = Group.objects.get(id=COLABORADOR_EMPRESA)

            # - Ver si es un cliente externo
            if grupoPersona.objects.filter(person_id=request.user.id, relacion_grupo_id__in=[9, 10]):
                query_group = Group.objects.get(id=CLIENTE_EXTERNO)

            # - Ver si es un beneficiario (personal externo)
            if grupoPersona.objects.filter(person_id=request.user.id, relacion_grupo_id=6):
                query_group = Group.objects.get(id=BeneficiarioDispersa)

            user = persona.objects.get(id=request.user.id)
            user.groups.add(query_group)

            # if request.user.is_superuser == False and request.user.is_staff == False:
            #     # - Si no tiene ninguno, poner usuario no autorizado
            #     errores.append(1)

        # if errores:
        #     raise PermissionDenied({"Error": {"code": ["400"]}, "status": ["ERROR"],
        #                             "detail": [{"field": "", "data": "",
        #                                         "message": "Usuario no autorizado"}]})
        try:
            grupo_security = Group.objects.get(name=user_log[0]['name'])
            permissionsGroup = grupo_security.permissions.all().values('codename', 'name')
            for permision in permissionsGroup:
                if permision['name'] in view.permisos:
                    if request.method == "GET":
                        if "view" in permision["codename"].split("_"):
                            return True
                    if request.method == "POST":
                        if "add" in permision["codename"].split("_"):
                            return True
                    if request.method == "DELETE":
                        if "delete" in permision["codename"].split("_"):
                            return True
                    if request.method == "PUT":
                        if "change" in permision["codename"].split("_"):
                            return True
        except:
            err = MyHttpError('Usted no tiene permiso para acceder a este sitio', real_error=None)
            # log.json_response(err.standard_error_responses())
            raise PermissionDenied(err.standard_error_responses())

        # if errores:
        #     raise PermissionDenied({"Error": {"code": ["400"]}, "status": ["ERROR"],
        #                             "detail": [{"field": "", "data": "",
        #                                         "message": "Usuario no autorizado"}]})
