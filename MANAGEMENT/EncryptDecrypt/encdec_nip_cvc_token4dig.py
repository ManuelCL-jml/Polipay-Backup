# -*- coding: utf-8 -*-

from pathlib import Path
import json
import subprocess

def encdec_nip_cvc_token4dig(accion : str, area : str, texto : str):
	# accion:	1(cifrar), 2(descifrar)
	# area:		BE(BackEnd), FE(FrontEnd), MO(Mobile), BD(BaseDeDatos)

	#fpath			= Path("../../../../MANAGEMENT/EncryptDecrypt/openssl.php").absolute()
	#fpath			= str(fpath).replace("../","")
	fpath			= Path("./MANAGEMENT/EncryptDecrypt/openssl.php").absolute()
	fpath			= str(fpath).replace("./","")
	cmdExt			= "php " + str(fpath) + " " + str(accion) + " " + str(area) +" \"" + str(texto) + "\""
	output			= subprocess.check_output(cmdExt, shell=True, universal_newlines=True)
	output			= output.strip()
	objJson			= json.loads( str(output) )
	return objJson
