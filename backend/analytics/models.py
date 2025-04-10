from django.db import models
from django.contrib.auth.models import AbstractUser


max_name_length = 300

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

class User(models.Model):
    name = models.CharField(max_length=max_name_length)
    rb_username = models.CharField(max_length=max_name_length, unique=True)
    rb_password = models.CharField(max_length=64)

class Token(models.Model):
    name = models.CharField(max_length=max_name_length)
    value = models.CharField(max_length=max_name_length, unique=True)
    VHOST_name = models.CharField(max_length=max_name_length)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, related_name='tokens', on_delete=models.CASCADE)

    def is_expired(self):
        return False

class Queue(models.Model):
    fullname = models.CharField(max_length=max_name_length)
    name = models.CharField(max_length=max_name_length)
    type = models.CharField(max_length=max_name_length)
    token = models.ForeignKey(Token, related_name='queues', on_delete=models.CASCADE)


# KPI Models

class Client(models.Model):
    cid = models.IntegerField()
    token = models.ForeignKey(Token, related_name='clients', on_delete=models.CASCADE)


class KPIData(models.Model):
    client = models.ForeignKey(Client, related_name='data', on_delete=models.CASCADE)
    token = models.ForeignKey(Token, related_name='data', on_delete=models.CASCADE)
    value = models.FloatField()
    time = models.DateTimeField(auto_now_add=True)

class GlobalKPIDaily(models.Model):
    token = models.ForeignKey(Token, related_name='global_data', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    total_users = models.IntegerField(default=0)
    daily_active_users = models.IntegerField(default=0)

    class Meta: 
        unique_together = ('token', 'date')
        get_latest_by = 'date'