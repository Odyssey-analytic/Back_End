from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, F, CheckConstraint
from django.contrib.postgres.fields import ArrayField
import os, hashlib, base64
from django.utils.crypto import get_random_string

max_name_length = 300

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_first_login = models.BooleanField(default=True)
    rb_username = models.CharField(max_length=max_name_length, unique=True)
    rb_password = models.CharField(max_length=64)

class Product(models.Model):
    name = models.TextField(max_length=max_name_length, blank=False, null=False, unique=True)
    description = models.TextField(max_length=500, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    owner = models.ForeignKey(CustomUser, related_name='products', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.thumbnail and not self.thumbnail.name.startswith('thumbnails/'):
            ext = os.path.splitext(self.thumbnail.name)[1]

            hash_bytes = hashlib.sha256(
                (self.thumbnail.name + get_random_string(100)).encode()
            ).digest()

            url_safe_hash = base64.urlsafe_b64encode(hash_bytes).decode().rstrip("=")

            short_hash = url_safe_hash[:32]

            self.thumbnail.name = f'{short_hash}{ext}'

        super().save(*args, **kwargs)



class Game(Product):

    class Platform(models.TextChoices):
        ANDROID = 'android', 'Android'
        PC =  'pc', 'PC'
        IOS = 'ios', 'IOS'

    engine = models.TextField(max_length=max_name_length, null=False)
    platform = ArrayField(
        models.CharField(max_length=7,choices=Platform.choices),
        default=list,
        blank=False)



class Token(models.Model):
    name = models.CharField(max_length=max_name_length)
    value = models.CharField(max_length=max_name_length, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    Product = models.ForeignKey(Product, related_name='tokens', on_delete=models.CASCADE)

    def is_expired(self):
        return False

class Queue(models.Model):
    fullname = models.CharField(max_length=max_name_length)
    name = models.CharField(max_length=max_name_length)
    type = models.CharField(max_length=max_name_length)
    token = models.ForeignKey(Token, related_name='queues', on_delete=models.CASCADE)

# session management

class Client(models.Model):
    id = models.IntegerField(primary_key=True)
    token = models.ForeignKey(Token, related_name='clients', on_delete=models.CASCADE)


class Session(models.Model):
    client = models.ForeignKey("Client", related_name="sessions", on_delete=models.CASCADE)
    token = models.ForeignKey("Token", related_name="sessions", on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    platform = models.TextField(max_length=100)
    duration = models.DurationField(editable=False, null=True)

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(start_time__lt=F('end_time')), name='start_before_end')
        ]


class GameEvent(models.Model):
    time = models.DateTimeField()
    client = models.ForeignKey(Client, related_name="events", on_delete=models.CASCADE)
    session = models.ForeignKey(Session, related_name="events", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="events", on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'gameevent'
# Events

class CustomEvent(models.Model):
    game_event = models.IntegerField()
    custom_field1 = models.TextField(max_length=64)
    custom_field2 = models.TextField(max_length=64)
    custom_field3 = models.TextField(max_length=64)
    custom_field4 = models.TextField(max_length=64)
    custom_field5 = models.TextField(max_length=64)
    float_value = models.FloatField(null=True, blank=True)



class SessionStartEvent(models.Model):
    game_event = models.IntegerField()
    platform = models.TextField(max_length=100, null=False)


class BussinessEvent(models.Model):
    cartType = models.CharField(max_length=max_name_length)
    itemType = models.CharField(max_length=max_name_length)
    itemId = models.CharField(max_length=max_name_length)
    amount = models.IntegerField()
    game_event = models.IntegerField()
    currency  = models.CharField(max_length=max_name_length)

class ErrorEvent(models.Model):
    game_event = models.IntegerField()
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=[('Info', 'Info'),
                                                        ('Debug', 'Debug'),
                                                        ('Warning', 'Warning'),
                                                        ('Error', 'Error'),
                                                        ('Critical', 'Critical')])


class ProgeressionEvent(models.Model):
    game_event = models.IntegerField()
    progressionStatus = models.CharField(max_length=max_name_length)
    progression01 = models.CharField(max_length=max_name_length)
    progression02 = models.CharField(max_length=max_name_length)
    progression03 = models.CharField(max_length=max_name_length)
    value = models.FloatField()


class QualityEvent(models.Model):
    game_event = models.IntegerField()
    FPS = models.FloatField()
    memoryUsage = models.FloatField()


class ResourceEvent(models.Model):
    game_event = models.IntegerField()
    flowType = models.CharField(max_length=max_name_length)
    itemType = models.CharField(max_length=max_name_length)
    itemId = models.CharField(max_length=max_name_length)
    amount = models.IntegerField()
    resourceCurrency = models.CharField(max_length=max_name_length)

class SessionEndEvent(models.Model):
    game_event = models.IntegerField()


# Materialized Views

class GameEventHourlyCount(models.Model):
    bucket = models.DateTimeField(primary_key=True)
    product = models.ForeignKey('Product', db_column='product_id', on_delete=models.DO_NOTHING)
    event_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'gameeventcount_hourly'
