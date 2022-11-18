import string
from rest_framework.serializers import *
from rest_framework.exceptions import ParseError

from polipaynewConfig.inntec import *
from polipaynewConfig.exceptions import *

from apps.users.models import *
from polipaynewConfig.settings import rfc_Bec


class SerializerAsignarTarjetasCuentaEje(Serializer):
    tarjeta = ListField()

    def validar_tarjetas(self,tarjetas):
        error = []
        datos_tarjeta_inntec = []
        token, _ = get_token()
        queryset = get_CardsStockMasivo(token)


        for numero_tarjeta in tarjetas:
            if len(numero_tarjeta) != 16:
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta no encontrada"})
            if tarjeta.objects.filter(tarjeta=numero_tarjeta):
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta registrada"})
            datos_tarjetas = listCardMasivo(numero_tarjeta,queryset)
            if datos_tarjetas:
                datos_tarjeta_inntec.append(datos_tarjetas)
            else:
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta registrada"})
        MensajeError(error)
        return tarjetas,datos_tarjeta_inntec,token

    def create(self, instance,tarjetas,datos_tarjeta_inntec,token):
        Clave_Empleado = ClaveEmpleadoMasivo(token,datos_tarjeta_inntec)

        tarjeta.objects.bulk_create([
            tarjeta(
                    tarjeta=datos["tarjeta"], is_active=False,
                    rel_proveedor_id=1,
                    TarjetaId=datos["TarjetaId"],
                    NumeroCuenta=datos["NumeroCuenta"],
                    status="04", clientePrincipal_id=instance.id,ClaveEmpleado=datos["ClaveEmpleado"],
                    deletion_date=datetime.datetime.now(),
            )for datos in Clave_Empleado
        ]
        )
        return tarjetas

class SerializerAsignarTarjetasCuentaEjePrueba(Serializer):
    # tarjeta = ListField()

    def validar_tarjetas(self,tarjetas):
        error = []
        datos_tarjeta_inntec = []
        token, _ = get_tokenInntecPruebas()
        # queryset = get_CardsStockMasivoPrueba(token)

        for numero_tarjeta in tarjetas:
            print("1")
            if len(numero_tarjeta) != 16:
                error.append({"field": "tarjeta", "data": numero_tarjeta,
                              "message": "Tarjeta no encontrada"})
            # datos_tarjetas = listCardMasivoPrueba(numero_tarjeta,queryset)
            # if datos_tarjetas:
                # datos_tarjeta_inntec.append(datos_tarjetas)
            datos_tarjeta_inntec.append(numero_tarjeta) # No
            # else:
            #     error.append({"field": "tarjeta", "data": numero_tarjeta,
            #                   "message": "Tarjeta registrada"})
        MensajeError(error)
        return tarjetas,datos_tarjeta_inntec,token

    def create(self, instance,tarjetas,datos_tarjeta_inntec,token):
        Clave_Empleado = ClaveEmpleadoMasivoPrueba(token,datos_tarjeta_inntec) #Prueba

        tarjeta.objects.bulk_create([
            tarjeta(
                    tarjeta=datos["tarjeta"], is_active=False,
                    rel_proveedor_id=1,
                    TarjetaId=datos["TarjetaId"],
                    NumeroCuenta=datos["NumeroCuenta"],
                    status="04", clientePrincipal_id=instance.id,ClaveEmpleado=datos["ClaveEmpleado"]
            )for datos in Clave_Empleado
        ]
        )
        return tarjetas


class SerializerAsignarTarjetasPersonaExterna(Serializer):
    tarjeta = ListField()

    def validate_tarjeta(self, data):
        error = []
        for i in data:
            datos = tarjeta.objects.filter(tarjeta=i, clientePrincipal_id=self.context['empresa_id'])
            if len(datos) != 0:
                continue
            else:
                error.append(i)
        if error:
            raise ValidationError({"code": ["400"], "status": ["error"],
                                   "detail": [{"message": "No se pudo asignar la tarjeta"},
                                              {"field": "tarjeta", "message": "Tarjeta no encontrada",
                                               "data": error}]})
        return data

    def update(self, instance, instanceP):
        numerotarjeta = self.validated_data.get("tarjeta")
        lista = []
        for numero_tarjeta in numerotarjeta:
            instanceTarjeta = tarjeta.objects.get(tarjeta=numero_tarjeta)
            if instanceTarjeta.status == "04":
                apellidos = SepararApellidos(instanceP)

                if apellidos[0] == "" or apellidos[0] == None:
                    apellido_paterno = "NA"
                else:
                    apellido_paterno = apellidos[0]
                if apellidos[1] == "" or apellidos[1] == None:
                    apellido_materno = "NA"
                else:
                    apellido_materno = apellidos[1]
                if instanceTarjeta.ClaveEmpleado == "" or instanceTarjeta.ClaveEmpleado == None:
                    nueva_clave = ClaveEmpleado()
                    instanceTarjeta.ClaveEmpleado = nueva_clave
                    instanceTarjeta.save()

                if instanceP.rfc == "" or instanceP.rfc == None:
                    rfc = rfc_Bec
                else:
                    rfc = instanceP.rfc


                diccionario = [
                    {
                        "TarjetaId": instanceTarjeta.TarjetaId,
                        "ClienteId": "C000682", #C000682 ----> Produccion, C000022 -----> Pruebas
                        "ProductoId": 56,
                        "Nombre": instanceP.name,
                        "ApellidoPaterno": apellido_paterno,
                        "ApellidoMaterno": apellido_materno,
                        "NombreCorto": "",
                        "RFC": rfc,
                        "CURP": "",
                        "NSS": "",
                        "Direccion": "",
                        "NumeroTelefonoMovil": "9999999999",
                        "NumeroTelefonoCasa": "9999999999",
                        "NumeroTelefonoTrabajo": "",
                        "Estado": "",
                        "Municipio": "",
                        "Ciudad": "",
                        "Colonia": "",
                        "CorreoElectronico": instanceP.email,
                        "CodigoPostal": "",
                        "MontoInicial": "0.0",
                        "ClaveEstado": "",
                        "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
                        "CodigoRetenedora": ""
                    }
                ]
                # print(diccionario)
                mensaje = AsignarTarjetaPersonaExternaInntec(diccionario) #Produccion
                # print(mensaje)
                # AsignarTarjetaPersonaExternaInntecPrueba(diccionario) #Pruebas
                instanceTarjeta.status = "00"
                instanceTarjeta.is_active = True
                instanceTarjeta.cuenta_id = instance.id
                instanceTarjeta.save()
                lista.append(numero_tarjeta)
            else:
                raise ValidationError({"code": ["400"], "status": ["error"],
                                       "detail": [{"message": "No se pudo asignar la tarjeta"},
                                                  {"field": "tarjeta", "message": "Tarjeta ya asignada",
                                                   "data": instanceTarjeta.tarjeta}]})
        return lista

class AsignarTarjetasBeneficiarioMasivo(Serializer):
    def validate_tarjeta(listado_excel,cuenta_eje,estado):
        error = []
        tarjetas = []
        tarjeta_duplicada = []
        if estado not in ["Prueba","Produccion"]:
            error.append({"field": "", "data": "",
                "message": "Estado no reconocido"})

        for datos in listado_excel:
            if datos['Tarjeta1'] == '' and datos['Tarjeta2'] == '' and datos['Tarjeta3'] == '' and datos['Tarjeta4'] == '' and datos['Tarjeta5'] == '':
                error.append({"field": "Tarjeta", "data": "",
                "message": "debe asignar al menos 1 tarjeta por beneficiario"})

            if datos['Tarjeta1'] != '':

                if datos['Tarjeta1'] in tarjetas:
                    if datos['Tarjeta1'] not in tarjeta_duplicada:
                        error.append({"field": "", "data": datos['Tarjeta1'],
                            "message": "Tarjeta duplicada"})
                        tarjeta_duplicada.append(datos['Tarjeta1'])

                if tarjeta.objects.filter(tarjeta=datos['Tarjeta1'], clientePrincipal_id=cuenta_eje,status='04',rel_proveedor_id=1):
                    tarjetas.append(datos['Tarjeta1'])

                else:
                    error.append({"field": "Tarjeta1", "data": datos['Tarjeta1'],
                        "message": "Tarjeta no encontrada o registrada"})

            if datos['Tarjeta2'] != '':

                if datos['Tarjeta2'] in tarjetas:
                    if datos['Tarjeta2'] not in tarjeta_duplicada:
                        error.append({"field": "", "data": datos['Tarjeta2'],
                            "message": "Tarjeta duplicada"})
                        tarjeta_duplicada.append(datos['Tarjeta2'])

                if tarjeta.objects.filter(tarjeta=datos['Tarjeta2'], clientePrincipal_id=cuenta_eje,status='04',rel_proveedor_id=1):
                    tarjetas.append(datos['Tarjeta2'])

                else:
                    error.append({"field": "Tarjeta2", "data": datos['Tarjeta2'],
                        "message": "Tarjeta no encontrada o registrada"})

            if datos['Tarjeta3'] != '':

                if datos['Tarjeta3'] in tarjetas:
                    if datos['Tarjeta3'] not in tarjeta_duplicada:
                        error.append({"field": "", "data": datos['Tarjeta3'],
                            "message": "Tarjeta duplicada"})
                        tarjeta_duplicada.append(datos['Tarjeta3'])

                if tarjeta.objects.filter(tarjeta=datos['Tarjeta3'], clientePrincipal_id=cuenta_eje,status='04',rel_proveedor_id=1):
                    tarjetas.append(datos['Tarjeta3'])

                else:
                    error.append({"field": "Tarjeta3", "data": datos['Tarjeta3'],
                        "message": "Tarjeta no encontrada o registrada"})

            if datos['Tarjeta4'] != '':

                if datos['Tarjeta4'] in tarjetas:
                    if datos['Tarjeta4'] not in tarjeta_duplicada:
                        error.append({"field": "", "data": datos['Tarjeta4'],
                            "message": "Tarjeta duplicada"})
                        tarjeta_duplicada.append(datos['Tarjeta4'])

                if tarjeta.objects.filter(tarjeta=datos['Tarjeta4'], clientePrincipal_id=cuenta_eje,status='04',rel_proveedor_id=1):
                    tarjetas.append(datos['Tarjeta4'])

                else:
                    error.append({"field": "Tarjeta4", "data": datos['Tarjeta4'],
                        "message": "Tarjeta no encontrada o registrada"})

            if datos['Tarjeta5'] != '':

                if datos['Tarjeta5'] in tarjetas:
                    if datos['Tarjeta5'] not in tarjeta_duplicada:
                        error.append({"field": "", "data": datos['Tarjeta5'],
                            "message": "Tarjeta duplicada"})
                        tarjeta_duplicada.append(datos['Tarjeta5'])

                if tarjeta.objects.filter(tarjeta=datos['Tarjeta5'], clientePrincipal_id=cuenta_eje,status='04',rel_proveedor_id=1):
                    tarjetas.append(datos['Tarjeta5'])

                else:
                    error.append({"field": "Tarjeta5", "data": datos['Tarjeta5'],
                        "message": "Tarjeta no encontrada o registrada"})

        MensajeError(error)
        return


    def Asignar_tarjetas(listado_excel,estado):
        diccionario_tarjetas = []
        client_id = None
        if estado == "Prueba":
            client_id = "C000022"

        if estado == "Produccion":
            client_id = "C000682"
        for datos_excel in listado_excel:
            tarjetas = [datos_excel.get('Tarjeta1'),datos_excel.get('Tarjeta2'),datos_excel.get('Tarjeta3'),datos_excel.get('Tarjeta4'),datos_excel.get('Tarjeta5')]
            for i in tarjetas:
                if i != "":
                    instanceTarjeta = tarjeta.objects.get(tarjeta=i)
                    cuenta_persona = cuenta.objects.get(cuenta=datos_excel.get('Numero_Cuenta'))
                    instance = persona.objects.get(id=cuenta_persona.persona_cuenta_id)
                    if instance.rfc == "" or instance.rfc == None:
                        rfc = rfc_Bec
                    else:
                        rfc = instance.rfc

                    if datos_excel.get('Apellido_paterno') == "":
                        apellido_paterno = "NA"

                    else:
                        apellido_paterno = datos_excel.get('Apellido_paterno')

                    if datos_excel.get('Apellido_materno') == "":
                        apellido_materno = "NA"
                    else:
                        apellido_materno = datos_excel.get('Apellido_materno')


                    if instanceTarjeta.ClaveEmpleado == "" or instanceTarjeta.ClaveEmpleado == None:
                        nueva_clave = None
                        if estado == "Prueba":
                            nueva_clave = ClaveEmpleadoIndividualPrueba()
                        if estado == "Produccion":
                            nueva_clave = ClaveEmpleado()
                        instanceTarjeta.ClaveEmpleado = nueva_clave
                        instanceTarjeta.save()

                    diccionario = {
                            "TarjetaId": instanceTarjeta.TarjetaId,
                            "ClienteId": client_id,
                            "ProductoId": 56,
                            "Nombre": datos_excel.get('Nombres'),
                            "ApellidoPaterno": apellido_paterno,
                            "ApellidoMaterno": apellido_materno,
                            "NombreCorto": "",
                            "RFC": rfc,
                            "CURP": "",
                            "NSS": "",
                            "Direccion": "",
                            "NumeroTelefonoMovil": "9999999999",
                            "NumeroTelefonoCasa": "9999999999",
                            "NumeroTelefonoTrabajo": "",
                            "Estado": "",
                            "Municipio": "",
                            "Ciudad": "",
                            "Colonia": "",
                            "CorreoElectronico": instance.email,
                            "CodigoPostal": "",
                            "MontoInicial": "0.0",
                            "ClaveEstado": "",
                            "NumeroEmpleado": instanceTarjeta.ClaveEmpleado,
                            "CodigoRetenedora": ""
                        }
                    # print(diccionario)
                    instanceTarjeta.status = "00"
                    instanceTarjeta.is_active = True
                    instanceTarjeta.cuenta_id = cuenta_persona.id
                    instanceTarjeta.save()
                    diccionario_tarjetas.append(diccionario)
        # print(diccionario_tarjetas)
        if estado == "Prueba":
            AsignarTarjetaPersonaExternaInntecPruebaMasivo(diccionario=diccionario_tarjetas)
        if estado == "Produccion":
            AsignarTarjetaPersonaExternaInntecMasivo(diccionario=diccionario_tarjetas)
        return
