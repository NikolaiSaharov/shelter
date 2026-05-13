from django.db import models

# Create your models here.

class Role(models.Model):
    role_id = models.AutoField(db_column='roleid', primary_key=True)
    role_name = models.CharField(db_column='rolename', max_length=20, unique=True)
    class Meta:
        db_table = 'roles'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
    def __str__(self):
        return self.role_name

class User(models.Model):
    user_id = models.AutoField(db_column='userid', primary_key=True)
    email = models.CharField(db_column='email', max_length=100, unique=True)
    password_hash = models.CharField(db_column='passwordhash', max_length=255)
    last_name = models.CharField(db_column='lastname', max_length=50)
    first_name = models.CharField(db_column='firstname', max_length=50)
    middle_name = models.CharField(db_column='middlename', max_length=50, null=True, blank=True)
    phone = models.CharField(db_column='phone', max_length=20)
    registration_date = models.DateTimeField(db_column='registrationdate', auto_now_add=True)
    role = models.ForeignKey(Role, models.DO_NOTHING, db_column='roleid')
    shelter = models.ForeignKey('animals.Shelter', models.SET_NULL, db_column='shelterid', null=True, blank=True)
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    def __str__(self):
        return f"{self.email} ({self.first_name} {self.last_name})"

class UserProfile(models.Model):
    profile_id = models.AutoField(db_column='profileid', primary_key=True)
    user = models.OneToOneField(User, models.CASCADE, db_column='userid', unique=True)
    home_address = models.CharField(db_column='homeaddress', max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(db_column='dateofbirth', null=True, blank=True)
    profile_picture = models.CharField(db_column='profilepicture', max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(db_column='createddate', auto_now_add=True)
    updated_date = models.DateTimeField(db_column='updateddate', auto_now=True)
    class Meta:
        db_table = 'userprofiles'
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    def __str__(self):
        return f"Профиль {self.user.email}"