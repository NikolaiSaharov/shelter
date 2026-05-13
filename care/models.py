from django.db import models
from animals.models import Animal


class ActivityType(models.Model):
    """Типы активностей для ухода за животными"""
    activity_type_id = models.AutoField(db_column='activitytypeid', primary_key=True)
    activity_name = models.CharField(db_column='activityname', max_length=100)
    description = models.TextField(db_column='description', null=True, blank=True)

    class Meta:
        db_table = 'activitytypes'
        verbose_name = 'Тип активности'
        verbose_name_plural = 'Типы активностей'

    def __str__(self):
        return self.activity_name


class FrequencyType(models.Model):
    """Типы частоты выполнения активностей"""
    frequency_id = models.AutoField(db_column='frequencyid', primary_key=True)
    frequency_name = models.CharField(db_column='frequencyname', max_length=50)

    class Meta:
        db_table = 'frequencytypes'
        verbose_name = 'Тип частоты'
        verbose_name_plural = 'Типы частоты'

    def __str__(self):
        return self.frequency_name


class AnimalCareSchedule(models.Model):
    """Расписание ухода за животными"""
    care_schedule_id = models.AutoField(db_column='scheduleid', primary_key=True)
    animal = models.ForeignKey(Animal, models.CASCADE, db_column='animalid')
    activity_type = models.ForeignKey(ActivityType, models.DO_NOTHING, db_column='activitytypeid')
    frequency = models.ForeignKey(FrequencyType, models.DO_NOTHING, db_column='frequencyid')
    schedule_time = models.TimeField(db_column='scheduletime', null=True, blank=True)
    notes = models.TextField(db_column='notes', null=True, blank=True)
    is_active = models.BooleanField(db_column='isactive', default=True)

    class Meta:
        db_table = 'animalcareschedule'
        verbose_name = 'Расписание ухода'
        verbose_name_plural = 'Расписание ухода'

    def __str__(self):
        return f"{self.animal.animal_name} - {self.activity_type.activity_name} ({self.frequency.frequency_name})"
