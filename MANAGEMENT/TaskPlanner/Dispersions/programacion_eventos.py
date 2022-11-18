from datetime import datetime

import os
from getpass import getuser
from pathlib import Path

from crontab import CronTab

# from polipaynewConfig.settings import COMMAND_CRONTAB


def create_schedule(date_schedule: str, comment: str):
    """
    Se crea la programación para la dispersion con la ayuda
    de crontab


    """
    try:
        dt_object1 = datetime.strptime(date_schedule, "%Y-%m-%d %H:%M:%S")
        cron = CronTab(user=getuser())

        t = f"{dt_object1.minute}{dt_object1.hour}{dt_object1.day}{dt_object1.month}{dt_object1.weekday()}"


        # job = cron.new(command=COMMAND_CRONTAB, comment=f'polipayTransaction_{comment}_{t}')
        # job.setall(dt_object1.minute, dt_object1.hour, dt_object1.day, dt_object1.month, dt_object1.weekday())
        # cron.write()

        return True

    except Exception as e:
        return print(e)
