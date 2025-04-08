from rest_framework import serializers
from .models import GameEvent, SessionStartEvent, SessionEndEvent, Session, Client
from rest_framework.validators import UniqueTogetherValidator

class GameEventSerializer(serializers.ModelSerializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        write_only=True
    )
    session_id = serializers.PrimaryKeyRelatedField(
        queryset=Session.objects.all(),
        source='session',
        write_only=True
    )
    
    class Meta:
        model = GameEvent
        fields = ['id', 'time', 'client', 'session']
        validators = [
            UniqueTogetherValidator(
                queryset=GameEvent.objects.all(),
                fields=['time', 'client', 'session'],
                message="This combination of time, client and session already exists."
            )
        ]

class SessionStartEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = SessionStartEvent
        fields = GameEventSerializer.Meta.fields + ['time', 'platform']
        

class SessionEndEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = SessionEndEvent
        fields = GameEventSerializer.Meta.fields