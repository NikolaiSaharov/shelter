from django.db import models
from accounts.models import User
from animals.models import Animal


class Donation(models.Model):
    """Пожертвование на животное"""
    donation_id = models.AutoField(db_column='donationid', primary_key=True)
    user = models.ForeignKey(User, models.CASCADE, db_column='userid')
    animal = models.ForeignKey(Animal, models.CASCADE, db_column='animalid')
    amount = models.DecimalField(db_column='amount', max_digits=10, decimal_places=2)
    donation_date = models.DateTimeField(db_column='donationdate', auto_now_add=True)
    comment = models.TextField(db_column='comment', null=True, blank=True)
    is_approved = models.BooleanField(db_column='isapproved', default=True)

    class Meta:
        db_table = 'donations'
        verbose_name = 'Пожертвование'
        verbose_name_plural = 'Пожертвования'

    def __str__(self):
        return f"Пожертвование #{self.donation_id} - {self.amount} руб."
