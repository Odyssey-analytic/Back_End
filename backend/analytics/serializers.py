from django.contrib.auth import authenticate
from django.db import connection
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_simplejwt.tokens import RefreshToken

from analytics.services.managers.QueueManager import RabbitAccountManager
from .models import CustomUser, GameEvent, SessionStartEvent, SessionEndEvent, Session, Product, Client, Game, \
    BussinessEvent, ErrorEvent, ProgeressionEvent, QualityEvent, ResourceEvent, CustomEvent


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
            raise serializers.ValidationError({"error": "Invalid username/email"})

        user = authenticate(username=identifier, password=password)

        if not user:
            # Check if identifier is email
            try:
                user_obj = CustomUser.objects.get(email=identifier)
                user = authenticate(username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None

        if not user:
            raise serializers.ValidationError({"error": "Invalid password"})

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
                VALUES (%s, %s, %s, %s) RETURNING id
                ''',
                [validated_data['time'], validated_data['client'].id, validated_data['session'].id,
                 validated_data['product'].id]
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


class BussinessEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)

    class Meta(GameEventSerializer.Meta):
        model = BussinessEvent
        fields = ['id', 'game_event', 'client', 'session', 'time', 'product'] + ['cartType', 'itemType', 'itemId','amount', 'currency']
        read_only_fields = ['game_event']                                                                        

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        product = validated_data.pop('product')
        cartType = validated_data.pop('cartType')
        itemType = validated_data.pop('itemType')
        itemId = validated_data.pop('itemId')
        amount = validated_data.pop('amount')
        currency = validated_data.pop('currency')

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

        business_event = BussinessEvent.objects.create(
            game_event=game_event.id,
            cartType=cartType,
            itemType=itemType,
            itemId=itemId,
            amount=amount,
            currency=currency
        )
        return business_event


class ErrorEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)
    
    class Meta(GameEventSerializer.Meta):
        model = ErrorEvent
        fields = ['id', 'game_event', 'client', 'session', 'time', 'product'] + ['message', 'severity']
        read_only_fields = ['game_event']

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        product = validated_data.pop('product')
        message = validated_data.pop('message')
        severity = validated_data.pop('severity')

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
            raise Exception(f"ErrorEvent serializer not valid")

        business_event = ErrorEvent.objects.create(
            game_event=game_event.id,
            message=message,
            severity=severity
        )
        return business_event


class ProgeressionEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)
    
    
    class Meta(GameEventSerializer.Meta):
        model = ProgeressionEvent
        fields = ['id', 'game_event', 'client', 'session', 'time', 'product'] + ['progressionStatus', 'progression01','progression02', 'progression03', 'value']
        read_only_fields = ['game_event']                                                                       
                                                                                

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        product = validated_data.pop('product')
        progressionStatus = validated_data.pop('progressionStatus')
        progression01 = validated_data.pop('progression01')
        progression02 = validated_data.pop('progression02')
        progression03 = validated_data.pop('progression03')
        value = validated_data.pop('value')

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
            raise Exception(f"ProgeressionEvent serializer not valid")

        business_event = ProgeressionEvent.objects.create(
            game_event=game_event.id,
            progressionStatus=progressionStatus,
            progression01=progression01,
            progression02=progression02,
            progression03=progression03,
            value=value
        )
        return business_event


class QualityEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)
    
    
    class Meta(GameEventSerializer.Meta):
        model = QualityEvent
        fields = ['id', 'game_event', 'client', 'session', 'time', 'product'] + ['FPS', 'memoryUsage']
        read_only_fields = ['game_event']
        
    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        product = validated_data.pop('product')
        FPS = validated_data.pop('FPS')
        memoryUsage = validated_data.pop('memoryUsage')

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
            raise Exception(f"QualityEvent serializer not valid")

        business_event = QualityEvent.objects.create(
            game_event=game_event.id,
            FPS=FPS,
            memoryUsage=memoryUsage
        )
        return business_event


class ResourceEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)
    
    
    class Meta(GameEventSerializer.Meta):
        model = ResourceEvent
        fields = GameEventSerializer.Meta.fields + ['flowType', 'itemType', 'itemId', 'amount', 'resourceCurrency']
        read_only_fields = ['game_event']

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
        return session_end_event

class CustomEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True)
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all(), write_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)
    time = serializers.DateTimeField(write_only=True)
    
    class Meta(GameEventSerializer.Meta):
        model = CustomEvent
        fields = ['id', 'game_event', 'client', 'session', 'time', 'product'] + ['custom_field1', 'custom_field2', 'custom_field3', 'custom_field4', 'custom_field5']
        read_only_fields = ['game_event']

    def create(self, validated_data):
        client = validated_data.pop('client')
        session = validated_data.pop('session')
        time = validated_data.pop('time')
        product = validated_data.pop('product')
        custom_field1 = validated_data.pop('custom_field1')
        custom_field2 = validated_data.pop('custom_field2')
        custom_field3 = validated_data.pop('custom_field3')
        custom_field4 = validated_data.pop('custom_field4')
        custom_field5 = validated_data.pop('custom_field5')

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
            raise Exception(f"CustomEvent serializer not valid")

        custom_event = CustomEvent.objects.create(
            game_event=game_event.id,
            custom_field1=custom_field1,
            custom_field2=custom_field2,
            custom_field3=custom_field3,
            custom_field4=custom_field4,
            custom_field5=custom_field5
        )
        return custom_event
