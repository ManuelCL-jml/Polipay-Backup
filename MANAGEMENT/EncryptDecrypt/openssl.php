<?php
# Caracteres que no crean conflicto en la consola de linux a ser cifrados: #$%&¡\/()+*.,:;¿?_-áéíóúÁÉÍÓÚ
# Caracter que crea conflicto en linux: !

# Recibe la acción: 1=cifrar, 2=descifrar.
$accion;
# Recibe el área que lo requiere: BE=BackEnd, FE=FrontEnd, MO=Mobile
$departamento;
# Texto: puede ser plano (legible) para ser cifrado  o cifrado para ser descifrado
$texto;

# Secretos (32 bytes, caracteres)
$S_BACKEND		= "P0l1m3nt3s#B4ck3ndXYZA.20210101_";
$S_FRONTEND		= "P0l1m3nt3s#Fr0nt3ndXYZ.20210101_";
$S_MOBILE		= "P0l1m3nt3s#M0b1l3XYZAB.20210101_";

$palabraSecreta		= "";
$textoCifrado		= "";
$textoDescifrado	= "";

$result			= "";
#$result			= array();

if( count($argv) == 4 ){
	# Recibe la acción: 1=cifrar, 2=descifrar.
	$accion			= trim($argv[1]);
	# Recibe el área que lo requiere: BE=BackEnd, FE=FrontEnd, MO=Mobile
	$departamento		= trim($argv[2]);
	# Texto: puede ser plano (legible) para ser cifrado  o cifrado para ser descifrado
	$texto			= trim($argv[3]);

	$metodoDeCifrado	= "AES-256-CBC";  // AES is used by the U.S. gov't to encrypt top secret documents.

	if( strcmp($departamento,"BE") == 0 ){
		$palabraSecreta		= "P0l1m3nt3s#B4ck3ndXYZA.20210101_";
	}else if( strcmp($departamento,"FE") == 0 ){
		$palabraSecreta		= "P0l1m3nt3s#Fr0nt3ndXYZ.20210101_";
	}else if( strcmp($departamento,"MO") == 0 ){
		$palabraSecreta		= "P0l1m3nt3s#M0b1l3XYZAB.20210101_";
	}else{
		#echo"\n\nValor para departamento incorrecta!! (".$departamento."), NADA por hacer.\n";
		#echo"	Ejemplo: php openssl.php <accion=1(cifrar)|2(descifrar)> <departament=BE(Backend)|FE=(FronEnd)|MO=Mobile> <texto>\n\n";
		$result	= "{\"status\":\"ERROR\", \"field\":\"departamento\",\"data\":\"".$departame."\",\"message\":\"Valor incorrecto.\"}";
		echo"\n\n".$result."\n\n";
		exit(1);
	}

	#$iv			= "0123456789012345";
	$iv			= "aZ.,-_$#XyZ069Az";

	if( $accion == 1 ){
		$textoCifrado		= openssl_encrypt($texto, $metodoDeCifrado, $palabraSecreta, false, $iv);
		#echo "\n\nTexto_Plano[".$texto."] size[".strlen($texto)."]\n";
		#echo "Encrypted[".$textoCifrado."] size[".strlen($textoCifrado)."]\n\n";
		$result	= "{\"status\":\"OK\", \"field\":\"cifrado\",\"data\":\"".$textoCifrado."\",\"numCaracteresTextoCifrado\":\"".strlen($textoCifrado)."\",\"message\":\"Cifrado correctamente.\",\"textoOriginal\":\"".$texto."\",\"numCaracteresTextoOri\":\"".strlen($texto)."\"}";
		echo"\n\n".$result."\n\n";
	}else if( $accion == 2 ){
		$textoDescifrado	= openssl_decrypt($texto, $metodoDeCifrado, $palabraSecreta, false, $iv);
		#echo "\n\nTexto_Plano[".$texto."] size[".strlen($texto)."]\n";
		#echo "Decrypted[".$textoDescifrado."] size[".strlen($textoDescifrado)."]\n\n";
		if( strlen($textoDescifrado) == 0 ){
			#echo "IMPORTANTE: Confirma que la opcion departamento(BE|FE|MO) concida con la contaseña que se utilizo para cifrar el texto! Algo no coincide.\n\n";
			$result	= "{\"status\":\"ERROR\", \"field\":\"descifrado\",\"data\":\"".$textoDescifrado."\",\"numCaracteresTextoDescifrado\":\"".strlen($textoDescifrado)."\",\"message\":\"Descifrado correctamente.\",\"textoOriginal\":\"".$texto."\",\"numCaracteresTextoOri\":\"".strlen($texto)."\",\"IMPORTANTE\":\"Confirma que la opcion departamento(BE|FE|MO) concida con la contraseña que se utilizo para cifrar el texto! Algo no coincide.\"}";
			echo"\n\n".$result."\n\n";
		}else{
			$result	= "{\"status\":\"OK\", \"field\":\"descifrado\",\"data\":\"".$textoDescifrado."\",\"numCaracteresTextoDescifrado\":\"".strlen($textoDescifrado)."\",\"message\":\"Descifrado correctamente.\",\"textoOriginal\":\"".$texto."\",\"numCaracteresTextoOri\":\"".strlen($texto)."\",\"IMPORTANTE\":\"---\"}";
			echo"\n\n".$result."\n\n";
		}
	}else{
		#echo"\n\nValor para acción incorrecta!! (".$accion."), NADA por hacer.\n";
		#echo"	Ejemplo: php openssl.php <accion=1(cifrar)|2(descifrar)> <departament=BE(Backend)|FE=(FronEnd)|MO=Mobile> <texto>\n\n";
		$result	= "{\"status\":\"ERROR\", \"field\":\"accion\",\"data\":\"".$accion."\",\"message\":\"Valor incorrecto.\"}";
		echo"\n\n".$result."\n\n";
		exit(1);
	}

}else{
	#echo"\n\nRecibe 3 argumentos! Mandaste: ".count($argv)."\n";
	#echo"	Ejemplo: php openssl.php <accion=1(cifrar)|2(descifrar)> <departament=BE(Backend)|FE=(FronEnd)|MO=Mobile> <texto>\n";
	#echo"	Ejemplo: php openssl.php 1 BE \"Hola Mundo\"\n";
	#echo"	Ejemplo: php openssl.php 1 BE \"\\\"Hola Mundo\\\"\" (para que pases las comillas como parte del texto a cifrar)\n\n";
	$result	= "{\"status\":\"ERROR\", \"field\":\"argumentos\",\"data\":".json_encode($argv).",\"message\":\"Numero de argumentos incorrectos. Recibe 3 argumentos!\"}";
	echo"\n\n".$result."\n\n";
}
?>
