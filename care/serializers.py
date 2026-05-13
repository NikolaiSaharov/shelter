from rest_framework import serializers
from .models import ActivityType, FrequencyType, AnimalCareSchedule
from animals.serializers import AnimalSerializer


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = '__all__'


class FrequencyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrequencyType
        fields = '__all__'


class AnimalCareScheduleSerializer(serializers.ModelSerializer):
    activity_type = ActivityTypeSerializer(read_only=True)
    frequency = FrequencyTypeSerializer(read_only=True)
    animal = AnimalSerializer(read_only=True)
    
    class Meta:
        model = AnimalCareSchedule
        fields = '__all__'
        depth = 1




