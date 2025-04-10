from rest_framework import serializers
from .models import User, CustomUser, GameEvent, SessionStartEvent, SessionEndEvent, Session, Client
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth import authenticate

class CustomUserSignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')  # Remove confirm_password from validated data
        user = CustomUser.objects.create_user(**validated_data)
        return user
    

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        user = authenticate(username=identifier, password=password)

        if not user:
            # Check if identifier is email
            try:
                user_obj = CustomUser.objects.get(email=identifier)
                user = authenticate(username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None

        if not user:
            raise serializers.ValidationError("Invalid username/email or password")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'username': user.username,
            'email': user.email
        }
      
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
