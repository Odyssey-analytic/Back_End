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
    
    class Meta:
        constraints = [
        models.UniqueConstraint(
            fields=['time', 'client', 'session'],
            name='unique_event'
        )
    ]
# Events

class SessionStartEvent(GameEvent):
    platform = models.TextField(max_length=100, null=False)
    

class SessionEndEvent(GameEvent):
    pass