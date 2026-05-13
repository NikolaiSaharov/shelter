from django.db import models


class AuditLog(models.Model):
    """Модель для аудитлога"""
    log_id = models.AutoField(db_column='logid', primary_key=True)
    user_id = models.IntegerField(db_column='userid', null=True, blank=True)
    action = models.CharField(db_column='action', max_length=50)
    entity_type = models.CharField(db_column='entitytype', max_length=50, null=True, blank=True)
    entity_id = models.IntegerField(db_column='entityid', null=True, blank=True)
    description = models.TextField(db_column='description', null=True, blank=True)
    timestamp = models.DateTimeField(db_column='timestamp', auto_now_add=True)
    ip_address = models.CharField(db_column='ipaddress', max_length=45, null=True, blank=True)
    
    class Meta:
        db_table = 'auditlogs'
        verbose_name = 'Запись аудитлога'
        verbose_name_plural = 'Аудитлог'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} - {self.timestamp}"

