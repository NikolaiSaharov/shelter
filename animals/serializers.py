from rest_framework import serializers
from .models import Animal, AnimalType, Breed, AnimalStatus, AnimalCharacter

class AnimalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = '__all__'

class BreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breed
        fields = '__all__'

class AnimalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalStatus
        fields = '__all__'

class AnimalCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalCharacter
        fields = '__all__'

class AnimalSerializer(serializers.ModelSerializer):
    status = AnimalStatusSerializer(read_only=True)
    breed = BreedSerializer(read_only=True)
    character = AnimalCharacterSerializer(read_only=True)
    class Meta:
        model = Animal
        fields = '__all__'
        depth = 1
