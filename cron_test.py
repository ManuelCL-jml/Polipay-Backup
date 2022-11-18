from polipaynewConfig.wsgi import *
from apps.users.models import persona
from apps.transaction.models import transferencia, TransMasivaProg
from apps.users.models import cuenta
from datetime import datetime
import dateutil.parser

from apps.api_client.sms import enviarSMS

if __name__ == '__main__':
    #run()
    programadas = transferencia.objects.filter(status_trans_id=3, programada=1)
    list_already_checked = []
    for programada in programadas:
        if programada.masivo_trans_id and programada.masivo_trans_id not in list_already_checked: #si tiene un id de dispersion masiva y si ya fue verificado su turno
            instance_trans_prog = TransMasivaProg.objects.filter(masivaReferida_id=programada.masivo_trans_id).first()
            if instance_trans_prog: #si existe un registro de dispersion masiva programada
                date_programada = dateutil.parser.parse(str(instance_trans_prog.fechaProgramada)).date()
                date_now = datetime.today().strftime('%Y-%m-%d') #fecha de hoy

                if str(date_programada) == str(date_now): #la fecha programda sea hoy
                    #dispersiones individuales que conforman la dispersion masiva (recuperada de la tabla transferencia)
                    list_to_be_process = transferencia.objects.filter(masivo_trans_id=instance_trans_prog.masivaReferida_id)
                    #por cada dispersion individual se recuperan los datos del emisor y el beneficiario, se actualizan los montos de ambos
                    #se le notifica al beneficiario via sms y se actualiza la dispersion individual a status_trans_id = 1 (liquidada)
                    for to_be_process in list_to_be_process:
                        instance_cuenta_emisor = cuenta.objects.filter(cuenta=to_be_process.cuenta_emisor).first()
                        cta_beneficiario = cuenta.objects.filter(cuenta=to_be_process.cta_beneficiario).first()
                        instance_persona_beneficiaria = persona.objects.filter(id=cta_beneficiario.persona_cuenta_id).first()

                        instance_cuenta_emisor.monto -= to_be_process.monto
                        instance_cuenta_emisor.save()

                        cta_beneficiario.monto += to_be_process.monto
                        cta_beneficiario.save()
                        # se notifica al beneficiario
                        enviarSMS(to_be_process.monto, instance_persona_beneficiaria)
                        #actualizar el estado de la transferencia
                        to_be_process.status_trans_id = 1
                        to_be_process.save()
                #se actualiza la fecha de ejecucion de la tabla TransMasivaProg de cada una de las dispersiones que conforma a la masiva
                list_dis_prog = TransMasivaProg.objects.filter(masivaReferida_id=programada.masivo_trans_id)
                for dis_prog in list_dis_prog:
                    dis_prog.fechaEjecucion = datetime.today()
                    dis_prog.save()
            #lista para agrupar a todas las dispersiones masivas que o ya les toco pasar o no les toca pasar el dia de hoy
            list_already_checked.append(programada.masivo_trans_id)
