from django.db import models
from accounts.models import User

class News(models.Model):
    news_id = models.AutoField(db_column='newsid', primary_key=True)
    user = models.ForeignKey(User, models.CASCADE, db_column='userid')
    title = models.CharField(db_column='title', max_length=100)
    content = models.TextField(db_column='content')
    post_date = models.DateTimeField(db_column='postdate', auto_now_add=True)
    is_published = models.BooleanField(db_column='ispublished', default=True)
    image_path = models.CharField(db_column='imagepath', max_length=255, null=True, blank=True)
    shelter = models.ForeignKey('animals.Shelter', models.SET_NULL, db_column='shelterid', null=True, blank=True)
    class Meta:
        db_table = 'news'
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
    def __str__(self):
        return self.title
