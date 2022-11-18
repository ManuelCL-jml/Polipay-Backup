from rest_framework import serializers
from apps.services_pay.models import *

class SerializerCategoryIn(serializers.Serializer):
	name = serializers.CharField()
	icon = serializers.CharField()

	def save(self):
		Category.objects.create(**self.validated_data)

	def update(self, instance, validated_data):
		instance.name = self.validated_data.get('name')
		instance.icon = self.validated_data.get('icon')
		instance.save()

class SerializerCategoryOut(serializers.Serializer):
	id = serializers.IntegerField()
	name = serializers.CharField()
	icon = serializers.CharField()

class SerializerReferenceIn(serializers.Serializer):
	catRel_id = serializers.IntegerField()
	id_transmitter = serializers.IntegerField()

	def save(self):
		instance = Transmitter.objects.get(id=self.validated_data.get('id_transmitter'))
		instance.catRel_id = self.validated_data.get('catRel_id')
		instance.save()
