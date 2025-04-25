from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from .services.managers.UserManager import GenerateToken
from .services.managers.QueueManager import RabbitAccountManager
from .models import Token, Queue, CustomUser, Client
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
from google.auth.transport import requests
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken


# Create your views here.
class SignInAPIView(APIView):
    """
    API View for rendering the sign-in page.
    """

    def get(self, request, *args, **kwargs):
        # Render the 'sign_in.html' template
        return render(request, 'sign_in.html')

class AuthReceiverAPIView(APIView):
    """
    Google calls this endpoint after the user has signed in with their Google account.
    """

    def post(self, request, *args, **kwargs):
        token = request.data.get('credential')

        if not token:
            return Response({"error": "Token is missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_data = id_token.verify_oauth2_token(
                token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID']
            )
        except ValueError:
            return Response({"error": "Invalid token."}, status=status.HTTP_403_FORBIDDEN)

        
        user_email = user_data.get('email')
        user = None
        try:
            user = CustomUser.objects.get(email__iexact=user_email)
        except CustomUser.DoesNotExist:
            None
        
        if not user:
            return Response({"error": "User does not exist with the email."}, status=status.HTTP_404_NOT_FOUND)
        
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
            return Response({'error': 'Token has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Validate the new password and confirmation
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not new_password or not confirm_password:
            return Response({'error': 'Both password fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password != confirm_password:
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
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
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
                        }
                    ]   
                )

                return Response({
                    'status': 'success',
                    'token': f'{token.value}'
                }, status=status.HTTP_201_CREATED)
            else:
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

            user = token_obj.user
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
