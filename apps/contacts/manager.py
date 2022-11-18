from django.db import models


class ManagerContacts(models.Manager):

    def filter_contacts_name(self, nombre: str, user_id: int):
        if nombre == 'null':
            nombre = ''
        return (
            super()
            .get_queryset()
            .filter(
                is_active=True,
                tipo_contacto_id=2,
                person_id=user_id,
                nombre__icontains=nombre
            )
            .values('id', 'nombre', 'alias', 'is_favorite')
            .order_by('id')
            .reverse()
        )

    # (ChrGil 2022-02-02) Crea contacto frecuente
    def create_contact(self, **kwargs):
        self.model(
            nombre=kwargs.pop('nombre'),
            cuenta=kwargs.pop('clabe'),
            banco=kwargs.pop('banco_id'),
            email=kwargs.pop('email'),
            alias=kwargs.pop('alias'),
            person_id=kwargs.pop('persona_id'),
            rfc_beneficiario=kwargs.pop('rfc_beneficiario'),
            is_favorite=True,
            tipo_contacto_id=2,
        ).save(using=self._db)


class ManagerGroupContact(models.Manager):

    def list_group_contacts(self, person_id: int):
        list_group = (
            super()
            .get_queryset()
            .select_related('contacts')
            .filter(
                contacts__person_id=person_id
            )
            .values_list('group_id', flat=True)
        )
        return list((set(list_group)))

    def get_groups_detail(self, group_id: int):#nuebvo
        list_group = (
            super()
            .get_queryset()
            .select_related('groups')
            .filter(
                group__id=group_id
            )
            .values_list('contacts_id', flat=True)
        )
        return list((set(list_group)))

