from rest_framework import serializers
from .models import User, UserProfile, Role

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        depth = 1

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True, source='userprofile')
    role = RoleSerializer(read_only=True)
    class Meta:
        model = User
        fields = '__all__'
        depth = 1
