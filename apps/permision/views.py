# Modulos nativos
import io

from django.contrib.auth.models import *
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.parsers import JSONParser

from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status, pagination
from rest_framework.exceptions import ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.pagination import PageNumberPagination

from datetime import datetime

# Modulos locales
from MANAGEMENT.Standard.errors_responses import MyHttpError
from MANAGEMENT.Utils.utils import get_values_list
from apps.users.models import *
from apps.permision.manager import *
from polipaynewConfig.settings import AdministrativoPolipayDispersa, AdministrativoPolipayEmpresa, AdministrativoPolipayLiberate
from polipaynewConfig.exceptions import NumInt
from .serializers import *
from .permisions import BlocklistPermission, BlocklistPermissionV2
from .models import *


class listPremision(viewsets.GenericViewSet):
    serializer_class = serializerPermisionOut
    queryset = Permission.objects.all()
    permission_classes = ()

    def list(self, request):
        query = Permission.objects.filter(codename__contains='_v1')
        serialzier = serializerPermisionOut(query, many=True)
        return Response(serialzier.data, status=status.HTTP_200_OK)


class createGroup(viewsets.GenericViewSet):
    serializer_class = serializerPermisionOut
    queryset = Group.objects.all()

    def create(self, request):
        new_Group, created = Group.objects.get_or_create(name=request.data['name'])
        query = Group.objects.get(name=new_Group)
        serializer = serializerGroupOut(query)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request):
        query = Group.objects.all()
        serializer = serializerGroupOut(query, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class addPermisionssGroups(viewsets.GenericViewSet):
    serializer_class = serializerGroupOut
    queryset = Group.objects.all()

    def create(self, request):
        try:
            query_group = Group.objects.get(id=request.data['id'])
            query_group.permissions.set(request.data['aPermissions'])
            return Response({"status": "Permisos agregados correctamente"}, status=status.HTTP_200_OK)
        except Exception as inst:
            raise ParseError({'status': 'Error al agregar permisos a grupo', "error": inst})


class addUSerGruop(viewsets.GenericViewSet):
    serializer_class = serializerGroupOut
    queryset = Group.objects.all()

    def create(self, request):
        try:
            query_group = Group.objects.get(id=request.data['idGroup'])
            user = persona.objects.get(id=request.data['idUSer'])
            consult_relation = user.groups.all().values('name')
            if len(consult_relation) > 0:
                return Response({"status": "Usuario ya pertenece al grupo: " + consult_relation[0]['name']},
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                user.groups.add(query_group)
            return Response({"status": "Usuario agregado éxitosamente"}, status=status.HTTP_200_OK)
        except Exception as inst:
            raise ParseError({'status': 'Error al agregar usuario a grupo', "error": inst})


class removePermisionssGroups(viewsets.GenericViewSet):
    serializer_class = serializerGroupOut
    queryset = Group.objects.all()

    def create(self, request):
        try:
            query_group = Group.objects.get(id=request.data['id'])
            for permission in request.data['aPermissions']:
                query_group.permissions.remove(permission)
            return Response({"status": "Permisos eliminados correctamente"}, status=status.HTTP_200_OK)
        except Exception as inst:
            raise ParseError({'status': 'Error al eliminar permisos a grupo', "error": inst})


class removeUSerGroup(viewsets.GenericViewSet):
    serializer_class = serializerGroupOut
    queryset = Group.objects.all()

    def create(self, request):
        try:
            user = persona.objects.get(id=request.data['idUser'])
            group = Group.objects.get(id=request.data['idGroup'])
            user.groups.remove(group)
            return Response({"status": "usuario eliminado de grupo"}, status=status.HTTP_200_OK)
        except Exception as inst:
            raise ParseError({'status': 'Error al eliminar usuario del grupo', "error": inst})


class deleteUSerGroup(viewsets.GenericViewSet):
    serializer_class = serializerGroupOut
    queryset = Group.objects.all()

    def create(self, request):
        Group.objects.get(id=request.data['idGroup']).delete()
        return Response({"status": "Se elimino el grupo éxitosamente"}, status=status.HTTP_200_OK)


########################################################################################################################

# end point para listar todos los permisos
class ListarPermisos(viewsets.GenericViewSet):
    # serializer_class = ListarPermisosOut
    permission_classes = ()

    def list(self, request):
        try:
            listado = []
            # Confirmar que el usuario sea un admin (P.D, P.E)
            verify_admin = grupoPersona.objects.filter(person_id=self.request.user.id, relacion_grupo_id__in=[1,3], is_admin=True).values('empresa_id')

            if len(verify_admin)==0:
                return Response({'code': 400, 'status': 'Error', 'Messague': 'No se encontraron registros'})

        except Exception as e:
            err = MyHttpError(message='Debe iniciar sesion como Administrativo Polipay Dispersa o Administrativo Polipay Empresa', real_error=str(e))
            return Response(err.standard_error_responses(), status=status.HTTP_400_BAD_REQUEST)

        else:
            # Recuperar el producto al que pertenece el usuario (cuenta)
            get_product = cuenta.objects.get(persona_cuenta_id=verify_admin[0]['empresa_id'])

            # condicionar en función del producto y se obtiene la lista de permisos en relacion al producto
            if get_product.rel_cuenta_prod_id == 1:
                query = Group.objects.filter(name='*Administrativo Polipay Dispersa')
                serializer = serializerGroupOut(query, many=True)
                json = JSONRenderer().render(serializer.data)
                stream = io.BytesIO(json)
                data = JSONParser().parse(stream)
                listPer = []
                for i in data:
                    pk = str(i.get("id"))
                    name = i.get("name")
                    for a in i.get("permissions"):
                        permiso = Permission.objects.get(id=a)
                        dicPer = {"id": a, "permiso": permiso.name}

                        if a in [244,365,245,246,282,283,284,285,286,287,288,289,290,291,292,293,294,
                                 295,296,297,298,299,301,304,306,307,308,309,310,311,318,319,320,327,
                                 328,329,330,331,332,333]:

                            listPer.append(dicPer)
                            dicUser = {"id": pk, "name": name, "permisos": listPer}
                            listado.append(dicUser)
                        else:
                            pass

            if get_product.rel_cuenta_prod_id == 3:
                query = Group.objects.filter(name='*Administrativo Polipay Empresa')
                serializer = serializerGroupOut(query, many=True)
                json = JSONRenderer().render(serializer.data)
                stream = io.BytesIO(json)
                data = JSONParser().parse(stream)
                listPer = []
                for i in data:
                    pk = str(i.get("id"))
                    name = i.get("name")
                    for a in i.get("permissions"):
                        permiso = Permission.objects.get(id=a)
                        dicPer = {"id": a, "permiso": permiso.name}

                        if a in [238,239,240,241,242,243,247,248,249,300,301,302,304,306,307,308,309,310,311,318,319,320,324,325,326]:
                            pass
                        else:
                            listPer.append(dicPer)
                            dicUser = {"id": pk, "name": name, "permisos": listPer}
                            listado.append(dicUser)

            return Response(listado, status=status.HTTP_200_OK)


# Crea solo el nombre del grupo sin los permisos
class CrearNombreGrupoPermisos(viewsets.GenericViewSet):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Crear grupo de permisos"]
    serializer_class = None
    permission_classes = ()

    def create(self, request):
        errores = []
        nameId = request.data["name"]
        try:
            grupoNew = Group.objects.create(name=nameId)
            query = Group.objects.filter(name=nameId)
            serializer = serializerGroupOut(query, many=True)
            json = JSONRenderer().render(serializer.data)
            stream = io.BytesIO(json)
            data = JSONParser().parse(stream)
            for i in data:
                pk = i.get("id")
            fecha = HistoricoGrupos.objects.create(fkGroup_id=pk, movimiento_id=1)
        except:
            errores.append({"field": "name", "data": nameId,
                            "message": "Nombre ya registrado"})
        if errores:
            return Response({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "Grupo Creado"}, status=status.HTTP_200_OK)


class ListarGrupoPermisos(viewsets.GenericViewSet):
    # permission_classes = (BlocklistPermissionV2,)
    # permisos = ["Ver grupo de permisos"]
    permission_classes = ()

    # end point para listar todos los permisos del grupo

    def list(self, request):
        name = self.request.query_params["name"]
        query = Group.objects.filter(name=name)
        serializer = serializerGroupOut(query, many=True)
        json = JSONRenderer().render(serializer.data)
        stream = io.BytesIO(json)
        data = JSONParser().parse(stream)
        listPer = []
        for i in data:
            pk = str(i.get("id"))
            name = i.get("name")
            for a in i.get("permissions"):
                permiso = Permission.objects.get(id=a)
                dicPer = {"id": a, "permiso": permiso.name}
                listPer.append(dicPer)
        dicUser = {"id": pk, "name": name, "permisos": listPer}
        return Response(dicUser, status=status.HTTP_200_OK)


# End point para ver todos los grupos de permisos de una cuenta eje
class ListarGruposDePermisoNombre(viewsets.GenericViewSet):
    # serializer_class = ListGruposPermisosNombre
    # pagination_class = PageNumberPagination
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Ver grupos de permisos"]
    # permission_classes = ()

    def render_json(self, **kwargs):
        return {
            "id": kwargs.get('fkGroup_id'),
            "name": kwargs.get('fkGroup__name').split("*")[1],
            "fechaRegistro": kwargs.get('fechaRegistro')
        }

    def list(self, request):
        size = self.request.query_params["size"]
        size = NumInt(size=size)
        pagination.PageNumberPagination.page_size = size
        razon_social_id = self.request.query_params["id"]

        # userList = []
        # queryset = Group.objects.all()

        list_groups_colaboradores = [i
             for i in Group.objects.all().values('id', 'name')
             if str(i.get('name')).split("*")[0] == str(razon_social_id)
        ]

        if list_groups_colaboradores:
            grupos = HistoricoGrupos.objects.filter(
                fkGroup_id__in=get_values_list('id', list_groups_colaboradores),
                movimiento_id=1
            ).values('fkGroup_id', 'fkGroup__name', 'fechaRegistro')

            grupos_colaboradores = [self.render_json(**i) for i in grupos]
            page = self.paginate_queryset(grupos_colaboradores)
            return Response(page, status=status.HTTP_200_OK)

        if not list_groups_colaboradores:
            page = self.paginate_queryset(list_groups_colaboradores)
            return Response(page, status=status.HTTP_200_OK)
        # for i in queryset:
        #     try:
        #         pk, nombre = str(i.name).split("*")
        #         if nameId == pk:
        #             i.name = nombre
        #             fecha = HistoricoGrupos.objects.get(fkGroup_id=i.id, movimiento_id=1)  # i.id
        #             print(fecha.fechaRegistro)
        #             # Fecha, Tiempo = str(fecha.fechaRegistro).split(" ")
        #             dicUser = {"id": i.id, "name": nombre, "fechaRegistro": str(fecha.fechaRegistro)}
        #             userList.append(dicUser)
        #     except Exception as e:
        #         continue


# End point para eliminar el grupo de permiso
class EliminarGrupoPermisos(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Eliminar grupo de permisos"]
    serializer_class = None

    def create(self, request):
        pass

    def delete(self, request):
        grupoPermiso = request.data['idGroup']
        query_group = ExistGroup(grupoPermiso)
        userCueEje = persona.objects.get(id=request.data['idUSer'])
        cuecen = grupoPersona.objects.filter(empresa_id=userCueEje.id, relacion_grupo_id=5)
        colaboradores = []
        colabSinRepetir = []
        for personId in cuecen:
            colab = grupoPersona.objects.filter(relacion_grupo_id=8, empresa_id=personId.person_id)
            for i in colab:
                colaboradores.append(i.person_id)
        if colaboradores:
            for i in colaboradores:
                if i not in colabSinRepetir:
                    colabSinRepetir.append(i)
            for users in colabSinRepetir:
                user = persona.objects.get(id=users)
                consult_relation = user.groups.all().values('name')
                if consult_relation:
                    if consult_relation[0]['name'] == query_group.name:
                        return Response(
                            {"status": {"messaje": "No se puede eliminar el grupo ya que existen colaboradores en el"}},
                            status=status.HTTP_400_BAD_REQUEST)
                    else:
                        continue
        
        fecha = HistoricoGrupos.objects.get(fkGroup_id=grupoPermiso)
        fecha.delete()
        query_group.delete()
        return Response({"status": "Grupo de permiso eliminado"}, status=status.HTTP_200_OK)


# End point para asignar permisos al grupo y modificar los permisos del grupo
class GrupoPermisos(viewsets.GenericViewSet):
    permission_classes = (BlocklistPermissionV2,)
    permisos = ["Crear grupo de permisos", "Editar grupo de permisos"]
    serializer_class = serializerGroupOut

    def put(self, request):
        errores = []
        aPermisos = request.data['aPermissions']
        name = request.data["nameGroup"]
        if aPermisos:
            pass
        else:
            errores.append({"field": "aPermisos", "data": aPermisos,
                            "message": "Debe asignar al menos un permiso"})
        pk = self.request.query_params["GruId"]
        query = Group.objects.filter(id=pk)
        query_group = Group.objects.get(id=pk)
        serializer = serializerGroupOut(query, many=True)
        json = JSONRenderer().render(serializer.data)
        stream = io.BytesIO(json)
        data = JSONParser().parse(stream)
        try:
            query_group.name = name
            query_group.save()
        except:
            pkG, nombre = name.split("*")
            errores.append({"field": "nameGroup", "data": nombre,
                            "message": "Nombre ya existe"})
        if errores:
            return Response({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]},
                            status=status.HTTP_400_BAD_REQUEST)
        for i in data:
            permisos = i.get("permissions")
        if permisos:
            for permission in permisos:
                query_group.permissions.remove(permission)
        else:
            pass
        query_group.permissions.set(aPermisos)
        return Response({"status": "Permisos editados"}, status=status.HTTP_200_OK)

    def create(self, request):
        errores = []
        pk_Group = self.request.query_params['GruId']
        try:
            query_group = Group.objects.get(id=pk_Group)
            if query_group.permissions.count():
                errores.append({"field": "", "data": "",
                                "message": "Ya tiene permisos este grupo"})
            else:
                pass
        except:
            errores.append({"field": "GruId", "data": pk_Group,
                            "message": "No se encontro ningun grupo"})
        if errores:
            return Response({"Error": {"code": ["400"]}, "status": ["ERROR"], "detail": [errores]},
                            status=status.HTTP_400_BAD_REQUEST)
        query_group.permissions.set(request.data['aPermissions'])
        return Response({"status": "Permisos asignados"}, status=status.HTTP_200_OK)


# End point para cambiar al usuario del permiso
class editarGrupoPermisoUser(viewsets.GenericViewSet):
    permission_classes = ()
    serializer_class = None

    def create(self, request):
        pass

    def put(self, request):
        pk = self.request.query_params["id"]
        user = persona.objects.get(id=pk)
        grupo = user.groups.all()
        try:
            group = Group.objects.get(id=grupo[0]["id"])
            user.groups.remove(group)
        except:
            pass
        NewGroup = Group.objects.get(id=request.data["GroupId"])
        user.groups.add(NewGroup)
        return Response({"status": "Usuario se cambio de grupo de permisos"}, status=status.HTTP_200_OK)

####### Pruebas
from MANAGEMENT.VoiceMail.send_call import *
from apps.users.management import createCodeCallCache

class ListarGruposDePermisoNombrePrueba(viewsets.GenericViewSet):  # Prueba
    serializer_class = ListGruposPermisosNombre
    pagination_class = PageNumberPagination
    # permission_classes = (BlocklistPermissionV2, )
    permission_classes = ()
    serializer_class = None

    def list(self, request):
        query_group = Group.objects.get(id=37) #37
        pk = self.request.query_params["id"]
        user = persona.objects.get(id=1387) ## id para asignar permisos a usuario
        consult_relation = user.groups.all().values('name')
        user.groups.add(query_group)


        #instance = persona.objects.get(id=86)
        #createCodeCallCache(instance)
        return Response("page 22", status=status.HTTP_200_OK)

