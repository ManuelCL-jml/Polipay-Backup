from django.test import TestCase


from apps.contacts.models import contactos

# Create your tests here.


contactos_instance =contactos.objects.get(person_id = 1314).values('cuenta')
print(contactos_instance)