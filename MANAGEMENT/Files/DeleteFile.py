# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
import subprocess
import os



def DeleteFile(filePathToDelete : str):
    #cmdExt = "rm " + str(filePathToDelete)
    #output = subprocess.check_output(cmdExt, shell=True, universal_newlines=True)
    #output = output.strip()

    try:
        os.remove(filePathToDelete)
    except OSError as e:
        #return {"status":str(e.strerror)}
        return True
    else:
        return False