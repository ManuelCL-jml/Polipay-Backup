from apps.users.models import grupoPersona, persona
import random
from django.db.models import Q
from django.db import models


def generate_code(size_number) -> str:
    code = ""
    arr1 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
            'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    arr2 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
            'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
            'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

    if size_number <= 4:
        code = "".join([str(random.choice(arr1)) for i in range(size_number)])
    elif size_number > 4:
        code = "".join([str(random.choice(arr2)) for i in range(size_number)])

    return code


class CredentialsManager(models.Manager):

	def create_username_password(self, id_cuenta_eje):
		code_username = generate_code(4)
		cuenta_eje_name = persona.objects.get(id=id_cuenta_eje).name
		username = cuenta_eje_name.replace(" ", "") + str(code_username)
		password = generate_code(10)

		return username, password


	def create_credentials(self, id_cuenta_eje):
		username, password = self.create_username_password(id_cuenta_eje=id_cuenta_eje)
		credentials = self.model(
			username=username,
			password=password,
			personaRel_id=id_cuenta_eje
		)
		#credentials.set_password(password)
		credentials.save(using=self._db)
		return True
