from rest_framework import serializers
from .models import Application
from accounts.serializers import UserSerializer
from animals.serializers import AnimalSerializer


class ApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    animal = AnimalSerializer(read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'
        depth = 1




