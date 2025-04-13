from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, F, CheckConstraint

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