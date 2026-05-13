from rest_framework import serializers
from .models import Donation
from accounts.serializers import UserSerializer
from animals.serializers import AnimalSerializer


class DonationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    animal = AnimalSerializer(read_only=True)
    
    class Meta:
        model = Donation
        fields = '__all__'
        depth = 1




