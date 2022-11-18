# import random
#
# from dataclasses import dataclass
# from typing import Dict
#
# from jwcrypto.jwk import JWK
# from jwcrypto.jwe import JWE
#
# from apps.api_dynamic_token.Credentials import Credentials
#
#
# # (ChrGil 2021-11-18) Clase que se encarga de crear un token JWE
# @dataclass
# class CreateJWECrypto:
# 	public_key_mobile = Credentials().get_public_key_mobile()
# 	public_key_web = Credentials().get_public_key_web()
# 	START: int = 1000
# 	END: int = 9999
# 	STEP: int = 4
# 	alg: str = "RSA-OAEP-256"
# 	enc: str = "A256CBC-HS512"
#
# 	# (ChrGil 2021-11-18) Convierte a bytes el codigo generado aleatoriamente
# 	def payload(self) -> bytes:
# 		return str(self.generate_code()).encode()
#
# 	# (ChrGil 2021-11-18) Genera un codigo aleatorio
# 	def generate_code(self) -> int:
# 		return random.randrange(self.START, self.END, self.STEP)
#
# 	# (ChrGil 2021-11-18) Cabecera para lo algorimos y cifrado
# 	def protected_header(self) -> Dict:
# 		return {
# 			"alg": self.alg,
# 			"enc": self.enc,
# 			"typ": "JWE",
# 		}
#
# 	# (ChrGil 2021-11-18) cifrado y Encriptación del token
# 	def jwe_encryp(self) -> JWE:
# 		return JWE(plaintext=self.payload(), protected=self.protected_header())
#
# 	def jwe_encryp_mobile(self) -> str:
# 		jwetoken = self.jwe_encryp()
# 		return self.sing_token(jwetoken, self.public_key_mobile)
#
# 	def jwe_encryp_web(self) -> str:
# 		jwetoken = self.jwe_encryp()
# 		return self.sing_token(jwetoken, self.public_key_web)
#
# 	# (ChrGil 2021-11-18) Agrega firma del cliente
# 	def sing_token(self, jwetoken: JWE, sing: JWK) -> str:
# 		jwetoken.add_recipient(sing)
# 		return jwetoken.serialize(compact=True)
