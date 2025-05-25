from rest_framework import serializers
from .models import CustomUser, GameEvent, SessionStartEvent, SessionEndEvent, Session,Product, Client, Game, BussinessEvent, ErrorEvent, ProgeressionEvent, QualityEvent, ResourceEvent
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth import authenticate
from analytics.services.managers.QueueManager import RabbitAccountManager
from django.db.models import Q
from django.db import connection

class CustomUserSignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if RabbitAccountManager.account_exist(data['username']):
            raise serializers.ValidationError({"username": "an account with this username exists!"})
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')  # Remove confirm_password from validated data
        account_manager = RabbitAccountManager(validated_data['username'])
        username, password = account_manager.create_account()
        validated_data['rb_username'] = username
        validated_data['rb_password'] = password

        user = CustomUser.objects.create_user(**validated_data)
        return user
    

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        query_set = CustomUser.objects.filter(Q(email=identifier) or Q(username=identifier))
        if not len(query_set):
            raise serializers.ValidationError({"error":"Invalid username/email"})
        
        user = authenticate(username=identifier, password=password)

        if not user:
            # Check if identifier is email
            try:
                user_obj = CustomUser.objects.get(email=identifier)
                user = authenticate(username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None

        if not user:
            raise serializers.ValidationError({"error":"Invalid password"})
        
        is_first_login = user.is_first_login
        if is_first_login:
            user.is_first_login = False
            user.save()
    
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'username': user.username,
            'email': user.email,
            'is_first_login': is_first_login
        }


class GameSerializer(serializers.ModelSerializer):
    platform = serializers.ListField(
        child=serializers.ChoiceField(choices=Game.Platform.choices),
        allow_empty=False 
    )
    
    class Meta:
        model = Game
        fields = '__all__'

    def validate_platform(self, value):
        if not value:
            raise serializers.ValidationError("At least one platform must be selected.")
        return value


class GameEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    class Meta:
        model = GameEvent
        fields = ['id', 'time', 'client', 'session', 'product']
        read_only_fields = ['id'] 

    def create(self, validated_data):
        with connection.cursor() as cursor:

            print(f'''
                INSERT INTO gameevent (time, client_id, session_id)
                VALUES ({validated_data['time']}, {validated_data['client'].id}, {validated_data['session'].id})
                RETURNING id
                ''',
            )

            cursor.execute(
                '''
                INSERT INTO gameevent (time, client_id, session_id, product_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                ''',
                [validated_data['time'], validated_data['client'].id, validated_data['session'].id,validated_data['product'].id]
            )
            row = cursor.fetchone()
        validated_data['id'] = row[0]
        id_ = validated_data.pop('id')
        return GameEvent(id=id_, **validated_data)


class SessionStartEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)

    class Meta:
        model = SessionStartEvent
        fields = ['id', 'game_event', 'platform', 'client', 'session', 'time', 'product']
        read_only_fields = ['game_event']

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        platform = validated_data.pop('platform')
        product = validated_data.pop('product')

        game_event_serializer = GameEventSerializer(
            data={
                'client': client.id,
                'session': session.id,
                'time': time,
                'product': product.id
            })
        if game_event_serializer.is_valid():
                game_event = game_event_serializer.save()
        else:
            raise Exception(f"gameevent serializer not valid")
        
        session_start_event = SessionStartEvent.objects.create(
            game_event=game_event.id,
            platform=platform
        )
        return session_start_event



class BussinessEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = BussinessEvent
        fields = GameEventSerializer.Meta.fields + ['cartType', 'itemType', 'itemId', 'amount', 'currency']


class ErrorEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = ErrorEvent
        fields = GameEventSerializer.Meta.fields + ['message', 'severity']


class ProgeressionEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = ProgeressionEvent
        fields = GameEventSerializer.Meta.fields + ['progressionStatus', 'progression01', 'progression02', 'progression03', 'value']


class QualityEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = QualityEvent
        fields = GameEventSerializer.Meta.fields + ['FPS', 'memoryUsage']


class ResourceEventSerializer(GameEventSerializer):
    class Meta(GameEventSerializer.Meta):
        model = ResourceEvent
        fields = GameEventSerializer.Meta.fields + ['flowType', 'itemType', 'itemId', 'amount', 'resourceCurrency']

class SessionEndEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)

    class Meta:
        model = SessionEndEvent
        fields = ['id', 'game_event', 'client', 'session', 'time']
        read_only_fields = ['game_event']

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')

        game_event = GameEvent.objects.create(client=client, session=session, time=time)
        session_end_event = SessionEndEvent.objects.create(
            game_event=game_event.id,
        )