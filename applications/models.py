from django.db import models
from accounts.models import User
from animals.models import Animal


class ApplicationStatus(models.Model):
    """Статус заявки на усыновление"""
    status_id = models.AutoField(db_column='statusid', primary_key=True)
    status_name = models.CharField(db_column='statusname', max_length=20, unique=True)

    class Meta:
        db_table = 'applicationstatuses'
        verbose_name = 'Статус заявки'
        verbose_name_plural = 'Статусы заявок'

    def __str__(self):
        return self.status_name


class Application(models.Model):
    """Заявка на усыновление животного"""
    application_id = models.AutoField(db_column='applicationid', primary_key=True)
    user = models.ForeignKey(User, models.CASCADE, db_column='userid')
    animal = models.ForeignKey(Animal, models.CASCADE, db_column='animalid')
    application_date = models.DateTimeField(db_column='applicationdate', auto_now_add=True)
    status = models.ForeignKey(ApplicationStatus, models.DO_NOTHING, db_column='statusid', default=1)
    reason = models.TextField(db_column='reason', null=True, blank=True)
    experience = models.TextField(db_column='experience', null=True, blank=True)
    housing_conditions = models.TextField(db_column='housingconditions', null=True, blank=True)
    comment = models.TextField(db_column='comment', null=True, blank=True)
    
    # Поле для обратной совместимости (deprecated, используйте status)
    @property
    def is_approved(self):
        """Возвращает True, если статус заявки 'Approved'"""
        return self.status.status_name == 'Approved' if self.status else False

    class Meta:
        db_table = 'applications'
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return f"Заявка #{self.application_id} - {self.user.email}"
