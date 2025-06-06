from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from .services.managers.UserManager import GenerateToken
from .services.managers.QueueManager import RabbitAccountManager
from .models import Token, Queue, CustomUser, Client, Game, CustomEvent, GameEvent
import json
import random
import jwt
import os
from .serializers import CustomUserSignUpSerializer, LoginSerializer, GameSerializer
from datetime import datetime, timedelta, timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count, Avg, Max, Min, F
from django.db.models.functions import TruncHour, TruncDay, TruncWeek
from django.utils.dateparse import parse_datetime


# Create your views here.
class SignInAPIView(APIView):
    """
    API View for rendering the sign-in page.
    """
    permission_classes = [AllowAny] 

    def get(self, request, *args, **kwargs):
        # Render the 'sign_in.html' template
        return render(request, 'sign_in.html')

class AuthReceiverAPIView(APIView):
    """
    Google calls this endpoint after the user has signed in with their Google account.
    """
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        token = request.data.get('credential')
        print(token)
        print(os.getenv('GOOGLE_OAUTH_CLIENT_ID'))
        if not token:
            return Response({"error": "Token is missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_data = id_token.verify_oauth2_token(
                token, google_requests.Request(), os.getenv('GOOGLE_OAUTH_CLIENT_ID')
            )
        except Exception as e:
            print(e)
            return Response({"error": "Invalid token."}, status=status.HTTP_403_FORBIDDEN)
        print(f"user data: {user_data}")        
        user_email = user_data.get('email')
        user = None
        try:
            user = CustomUser.objects.get(email__iexact=user_email)
        except CustomUser.DoesNotExist:
            None
        
        message = "User loged in successfully."
        if not user:
            data = {"username": user_email, "email": user_email, "password": token, 'confirm_password': token}
            serializer = CustomUserSignUpSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                print(serializer.errors)
                message = "User object created successfully!"
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        is_first_login = user.is_first_login
        if is_first_login:
            user.is_first_login = False
            user.save()
    
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'username': user.username,
            'email': user.email,
            'is_first_login': is_first_login,
            'message': message,
            
        }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request, token):
        sec_key = settings.SECRET_KEY
        # Decode the token
        try:
            payload = jwt.decode(token, sec_key, algorithms=['HS256'])
            user_id = payload['user_id']
            user = CustomUser.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            print("jwt.ExpiredSignatureError")
            return Response({'error': 'Token has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            print("jwt.InvalidTokenError")
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            print("CustomUser.DoesNotExist")
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Fuck you")
            return Response({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Validate the new password and confirmation
        new_password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')
        
        if not new_password or not confirm_password:
            print("one field is empty")
            return Response({'error': 'Both password fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password != confirm_password:
            print("passwords do not match")
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the user's password
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny] 
    def post(self, request):
        try:
            sec_key = settings.SECRET_KEY
            email = request.data.get('email')
            user = CustomUser.objects.get(email=email)
            
            # Generate a JWT token for password reset
            payload = {
                'user_id': user.id,
                'exp': datetime.now(timezone.utc) + timedelta(hours=1),  # Expires in 1 hour
                'iat': datetime.now(timezone.utc)
            }
            token = jwt.encode(payload, sec_key, algorithm='HS256')
            
            # Generate a reset link (adjust the URL for your frontend)
            reset_link = f"http://odysseyanalytics.ir/reset-password/{token}"
            
            # Send reset link via email
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {reset_link}',
                'oddysey.analytics@gmail.com',
                [email],
            )
            print("Password reset link sent.")
            return Response({'message': 'Password reset link sent.'}, status=200)
        except CustomUser.DoesNotExist:
            print(e)
            return Response({'error': 'User not found.'}, status=404)
        except Exception as e:
            print(e)
            return Response({'error': e}, status=500)


class CustomUserSignUpView(APIView):
    permission_classes = [AllowAny] 
    serializer_class = CustomUserSignUpSerializer

    def post(self, request):
        serializer = CustomUserSignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            print(serializer.errors)
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny] 
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)        

class GameView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # if not request.user.has_perm('backend.add_game'):
            #     raise PermissionDenied("You don't have permission to create games")

            # Create a mutable copy of request.data
            request_data = request.data.copy()
            request_data['owner'] = request.user.id
            
            owner = CustomUser.objects.get(id=request.user.id)
            serializer = GameSerializer(data=request_data, context={'request': request})
            
            if serializer.is_valid():
                game = serializer.save()
                
                token = GenerateToken(
                    request_data["name"], 
                    owner.rb_username, 
                    game, 
                    [
                        {
                            "queue_name": "start_session",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "end_session",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "business_event",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "error_event",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "progression_event",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "quality_event",
                            "queue_type": "SINGLE_VALUE"
                        },
                        {
                            "queue_name": "resource_event",
                            "queue_type": "SINGLE_VALUE"
                        }
                    ]   
                )

                return Response({
                    'status': 'success',
                    'token': f'{token.value}'
                }, status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response({
                    'status': 'error',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except PermissionDenied as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        
        except Exception as e:     
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            games = Game.objects.filter(owner=request.user)
            
            serializer = GameSerializer(games, many=True, context={'request': request})
            
            processed_games = []
            for game in serializer.data:
                game_data = {k: v for k, v in game.items() if k != 'owner'}
                
                game_data['has_thumbnail'] = game['thumbnail'] is not None
                game_data['platform_count'] = len(game['platform'])

                game_data["retention"] = "125"
                game_data["DNU"] = "2405"
                game_data["DAU"] = "20"

                game_data["retention_delta"] = "+10.45%"
                game_data["DNU_delta"] = "-20.4%"
                game_data["DAU_delta"] = "+15%"

                processed_games.append(game_data)


            return Response({
                'status': 'success',
                'games': processed_games
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred while fetching games',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request):
        try:            
            token_value = request.headers.get('Authorization')
            if not token_value:
                raise NotFound('Token not provided or invalid.') 

            try:
                token_obj = Token.objects.get(value=token_value)
            except Token.DoesNotExist:
                raise AuthenticationFailed('Invalid token.')

            if token_obj.is_expired():
                raise AuthenticationFailed('Token has expired.')

            user = token_obj.Product.owner
            queues = Queue.objects.filter(token=token_obj)

            queue_data = [{"fullname": queue.fullname, "name": queue.name} for queue in queues]

            max_attempts = 10
            for _ in range(max_attempts):
                random_id = random.randint(1, 100000)
                if not Client.objects.filter(id=random_id).exists():
                    break
            else:
                return Response({"error": "Could not generate a unique client ID."}, status=500)

            client = Client.objects.create(id=random_id, token=token_obj)

            return Response({
                "rb_username": user.rb_username,
                "rb_password": user.rb_password,
                "queues": queue_data,
                "cid": client.id
            })

        except Exception as e:
            print(e)
            return Response({"error": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            data = json.loads(request.body)

            manager = UserManager(data["username"])
            token = manager.add_token(data["name"], data["queues"])

            return Response({'token': token.value})
        except Exception as e:
            print(e)
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomEventQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def get_trunc_function(self, bucket):
        if bucket == 'hourly':
            return TruncHour
        elif bucket == 'daily':
            return TruncDay
        elif bucket == 'weekly':
            return TruncWeek
        else:
            raise ValueError("Invalid bucket type. Must be one of: hourly, daily, weekly")

    def get_aggregate_function(self, aggregate_type):
        if aggregate_type == 'sum':
            return Sum('float_value')
        elif aggregate_type == 'count':
            return Count('id')
        elif aggregate_type == 'average':
            return Avg('float_value')
        elif aggregate_type == 'max':
            return Max('float_value')
        elif aggregate_type == 'min':
            return Min('float_value')
        else:
            raise ValueError("Invalid aggregate type. Must be one of: sum, count, average, max, min")

    def get(self, request):
        try:
            custom_field1 = request.query_params.get('custom_field1', '*')
            custom_field2 = request.query_params.get('custom_field2', '*')
            custom_field3 = request.query_params.get('custom_field3', '*')
            custom_field4 = request.query_params.get('custom_field4', '*')
            custom_field5 = request.query_params.get('custom_field5', '*')
            aggregate_type = request.query_params.get('aggregate_type')
            bucket = request.query_params.get('bucket')
            start_time = parse_datetime(request.query_params.get('starttime'))
            end_time = parse_datetime(request.query_params.get('endtime'))

            if not all([aggregate_type, bucket, start_time, end_time]):
                return Response({
                    'status': 'error',
                    'message': 'Missing required parameters'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate that wildcards only appear after non-wildcards
            fields = [custom_field1, custom_field2, custom_field3, custom_field4, custom_field5]
            found_wildcard = False
            for i, field in enumerate(fields):
                if field == '*':
                    found_wildcard = True
                elif found_wildcard:
                    return Response({
                        'status': 'error',
                        'message': 'Invalid field pattern - wildcards must be at the end'
                    }, status=status.HTTP_400_BAD_REQUEST)

            query = CustomEvent.objects.filter(
                game_event__in=GameEvent.objects.filter(
                    time__gte=start_time,
                    time__lte=end_time
                ).values('id')
            )

            if custom_field1 != '*':
                query = query.filter(custom_field1=custom_field1)
            if custom_field2 != '*':
                query = query.filter(custom_field2=custom_field2)
            if custom_field3 != '*':
                query = query.filter(custom_field3=custom_field3)
            if custom_field4 != '*':
                query = query.filter(custom_field4=custom_field4)
            if custom_field5 != '*':
                query = query.filter(custom_field5=custom_field5)

            trunc_func = self.get_trunc_function(bucket)
            agg_func = self.get_aggregate_function(aggregate_type)

            results = query.annotate(
                bucket=trunc_func('game_event__time')
            ).values(
                'bucket'
            ).annotate(
                value=agg_func
            ).order_by('bucket')

           
            response_data = [{
                'timestamp': bucket['bucket'].isoformat(),
                'value': bucket['value']
            } for bucket in results]

            return Response({
                'status': 'success',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
