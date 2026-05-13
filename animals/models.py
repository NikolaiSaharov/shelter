from django.db import models

# Create your models here.

class AnimalType(models.Model):
    type_id = models.AutoField(db_column='typeid', primary_key=True)
    type_name = models.CharField(db_column='typename', max_length=50, unique=True)

    class Meta:
        db_table = 'animaltypes'
        verbose_name = 'Тип животного'
        verbose_name_plural = 'Типы животных'
    def __str__(self):
        return self.type_name

class Breed(models.Model):
    breed_id = models.AutoField(db_column='breedid', primary_key=True)
    breed_name = models.CharField(db_column='breedname', max_length=100, unique=True)
    type = models.ForeignKey(AnimalType, models.CASCADE, db_column='typeid')

    class Meta:
        db_table = 'breeds'
        verbose_name = 'Порода'
        verbose_name_plural = 'Породы'
    def __str__(self):
        return self.breed_name

class AnimalStatus(models.Model):
    status_id = models.AutoField(db_column='statusid', primary_key=True)
    status_name = models.CharField(db_column='statusname', max_length=20, unique=True)

    class Meta:
        db_table = 'animalstatuses'
        verbose_name = 'Статус животного'
        verbose_name_plural = 'Статусы животных'
    def __str__(self):
        return self.status_name

class AnimalCharacter(models.Model):
    character_id = models.AutoField(db_column='characterid', primary_key=True)
    character_name = models.CharField(db_column='charactername', max_length=50, unique=True)
    description = models.CharField(db_column='description', max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'animalcharacters'
        verbose_name = 'Характер животного'
        verbose_name_plural = 'Характеры животных'
    def __str__(self):
        return self.character_name

class Shelter(models.Model):
    shelter_id = models.AutoField(db_column='shelterid', primary_key=True)
    shelter_name = models.CharField(db_column='sheltername', max_length=100, unique=True)
    address = models.CharField(db_column='address', max_length=255, null=True, blank=True)
    phone = models.CharField(db_column='phone', max_length=20, null=True, blank=True)
    email = models.CharField(db_column='email', max_length=100, null=True, blank=True)
    description = models.TextField(db_column='description', null=True, blank=True)
    is_active = models.BooleanField(db_column='isactive', default=True)
    created_date = models.DateTimeField(db_column='createddate', auto_now_add=True)

    class Meta:
        db_table = 'shelters'
        verbose_name = 'Приют'
        verbose_name_plural = 'Приюты'
    
    def __str__(self):
        return self.shelter_name

class Animal(models.Model):
    animal_id = models.AutoField(db_column='animalid', primary_key=True)
    animal_name = models.CharField(db_column='animalname', max_length=50)
    age = models.IntegerField(db_column='age')
    gender = models.CharField(db_column='gender', max_length=10)
    vaccinated = models.BooleanField(db_column='vaccinated', default=False)
    description = models.TextField(db_column='description', null=True, blank=True)
    image_path = models.CharField(db_column='imagepath', max_length=255, null=True, blank=True)
    status = models.ForeignKey(AnimalStatus, models.DO_NOTHING, db_column='statusid', default=1)
    breed = models.ForeignKey(Breed, models.CASCADE, db_column='breedid')
    character = models.ForeignKey(AnimalCharacter, models.SET_NULL, db_column='characterid', null=True, blank=True)
    height = models.DecimalField(db_column='height', max_digits=5, decimal_places=2, null=True, blank=True)
    animal_weight = models.DecimalField(db_column='animalweight', max_digits=5, decimal_places=2, null=True, blank=True)
    admission_date = models.DateField(db_column='admissiondate', null=True, blank=True)
    shelter = models.ForeignKey(Shelter, models.SET_NULL, db_column='shelterid', null=True, blank=True)

    class Meta:
        db_table = 'animals'
        verbose_name = 'Животное'
        verbose_name_plural = 'Животные'
    def __str__(self):
        return self.animal_name

class AnimalMedia(models.Model):
    """Медиа-файлы животных (фото и видео)"""
    MEDIA_TYPE_CHOICES = [
        ('Photo', 'Фото'),
        ('Video', 'Видео'),
    ]
    
    media_id = models.AutoField(db_column='mediaid', primary_key=True)
    animal = models.ForeignKey(Animal, models.CASCADE, db_column='animalid', related_name='media_files')
    media_type = models.CharField(db_column='mediatype', max_length=10, choices=MEDIA_TYPE_CHOICES)
    media_path = models.CharField(db_column='mediapath', max_length=500)
    display_order = models.IntegerField(db_column='displayorder', default=0)
    is_primary = models.BooleanField(db_column='isprimary', default=False)
    created_date = models.DateTimeField(db_column='createddate', auto_now_add=True)

    class Meta:
        db_table = 'animalmedia'
        verbose_name = 'Медиа-файл животного'
        verbose_name_plural = 'Медиа-файлы животных'
        ordering = ['display_order', 'media_id']

    def __str__(self):
        return f"{self.media_type} для {self.animal.animal_name}"