# from django.contrib.auth.models import GroupManager
#
# class ManageP(GroupManager):
from abc import ABC, abstractmethod
from typing import NoReturn, List, ClassVar, Union

from django.contrib.auth.models import *
from rest_framework.exceptions import ValidationError

from polipaynewConfig.settings import Admin, SuperAdmin, AdministrativoPolipayDispersa, BeneficiarioDispersa, \
    ADMIN_DISPERSA, ADMIN_LIBERATE, ADMIN_EMPRESA
from apps.users.models import *


# Verificar si existe grupo de permiso

def ExistGroup(grupoPermiso):
    try:
        query_group = Group.objects.get(id=grupoPermiso)
        return query_group
    except:
        raise ValidationError(
            {"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [{"field": "GroupP", "data": grupoPermiso,
                                                                          "message": "Grupo de permiso no encontrado"}]})


# Asignar usuario a grupo permiso
def UserAddGroup(grupoPermiso, colaborador):
    query_group = Group.objects.get(id=grupoPermiso)
    user = persona.objects.get(id=colaborador.id)
    user.groups.add(query_group)
    return True


# Asignar usuario a grupo permiso
def add_group_permission(group_id: int, person_id: int):
    query_group = Group.objects.get(id=group_id)
    user = persona.objects.get(id=person_id)
    user.groups.add(query_group)


# Asignar usuario a grupo permiso y elimina del nuevo grupo
def update_group_permission(group_id: int, person_id: int) -> bool:
    user = persona.objects.get(id=person_id)
    groups: List[Group] = user.groups.all()

    for i in groups:
        if i.id != group_id:
            user.groups.remove(i)

    user.groups.add(Group.objects.get(id=group_id))
    return True


# Asignar usuario a administrador(administrador polipay)
def AdminAddGroup(instance):
    query_group = Group.objects.get(id=Admin)
    user = persona.objects.get(id=instance.id)
    user.groups.add(query_group)
    return True


# Asignar usuario a administrativo(admin de una cuenta eje)
def AdminCueEjeAddGroup(instance):
    query_group = Group.objects.get(id=AdministrativoPolipayDispersa)
    user = persona.objects.get(id=instance.id)
    user.groups.add(query_group)
    return True


# Asignar usuario a Super Admin
def SuperAdminAddGroup(instance):
    query_group = Group.objects.get(id=SuperAdmin)
    user = persona.objects.get(id=instance.id)
    user.groups.add(query_group)
    return True


# Asignar usuario a BeneficiarioDispersa
def BeneficiarioDispersaAddGroup(instance):
    query_group = Group.objects.get(id=BeneficiarioDispersa)
    user = persona.objects.get(id=instance.id)
    user.groups.add(query_group)
    return True


# # Asignar usuario a Super Admin se duplico
# def SuperAdminAddGroup(instance):
#     query_group = Group.objects.get(id=SuperAdmin)
#     user = persona.objects.get(id=instance.id)
#     user.groups.add(query_group)
#     return True


# Cambiar el grupo de permiso de un usuario

def UserEditGroup(colaborador, groupId):
    user = persona.objects.get(id=colaborador)
    grupo = user.groups.all()
    try:
        group = Group.objects.get(id=grupo[0]["id"])
        user.groups.remove(group)
    except:
        pass
        NewGroup = Group.objects.get(id=groupId)
        user.groups.add(NewGroup)
    return True


# Ver los permisos de un usuario

def ListPermission(pk):
    try:
        user = persona.objects.get(id=pk)
        user_log = user.groups.all().values("name")
        grupo_security = Group.objects.get(name=user_log[0]['name'])
        permissionsGroup = grupo_security.permissions.all().values('id', 'name')
        return permissionsGroup
    except:
        pass


class ToAassignPermission(ABC):
    _group_permission: ClassVar[int]

    @abstractmethod
    def assing_permission_to_admin(self) -> NoReturn:
        ...


class PermissionDispersa(ToAassignPermission):
    def __init__(self, admin_list: Union[List[int], int]):
        self._admin_list = admin_list

        if isinstance(admin_list, int):
            self._admin_list = [admin_list]

        self._group_permission = ADMIN_DISPERSA
        self.assing_permission_to_admin()

    def assing_permission_to_admin(self):
        for admin_id in self._admin_list:
            user = persona.objects.get(id=admin_id)
            user.groups.add(Group.objects.get(id=self._group_permission))


class PermissionLiberate(ToAassignPermission):
    def __init__(self, admin_list: Union[List[int], int]):
        self._admin_list = admin_list

        if isinstance(admin_list, int):
            self._admin_list = [admin_list]

        self._group_permission = ADMIN_LIBERATE
        self.assing_permission_to_admin()

    def assing_permission_to_admin(self):
        for admin_id in self._admin_list:
            user = persona.objects.get(id=admin_id)
            user.groups.add(Group.objects.get(id=self._group_permission))


class PermissionEmpresa(ToAassignPermission):
    def __init__(self, admin_list: Union[List[int], int]):
        self._admin_list = admin_list

        if isinstance(admin_list, int):
            self._admin_list = [admin_list]

        self._group_permission = ADMIN_EMPRESA
        self.assing_permission_to_admin()

    def assing_permission_to_admin(self):
        for admin_id in self._admin_list:
            user = persona.objects.get(id=admin_id)
            user.groups.add(Group.objects.get(id=self._group_permission))
