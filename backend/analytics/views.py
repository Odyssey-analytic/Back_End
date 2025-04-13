from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from .services.managers.UserManager import UserManager
from .models import Token, Queue, CustomUser, Client
import json
import random
import jwt
from .serializers import CustomUserSignUpSerializer, LoginSerializer
from datetime import datetime, timedelta, timezone
from django.core.mail import send_mail
from django.conf import settings


# Create your views here.
class PasswordResetConfirmView(APIView):
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
            reset_link = f"http://odysseyanalytics.ir/api/reset-password/{token}"
            
            # Send reset link via email
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {reset_link}',
                'oddysey.analytics@gmail.com',
                [email],
            )
            
            return Response({'message': 'Password reset link sent.'}, status=200)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)
        except Exception as e:
            return Response({'error': e}, status=500)


class CustomUserSignUpView(APIView):

    serializer_class = CustomUserSignUpSerializer

    def post(self, request):
        serializer = CustomUserSignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):

    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserView(APIView):
    def post(self, request):
        print(f"Fuck YOU {request.body}")
        try:
            
            data = json.loads(request.body)
            
            manager = UserManager()
            user = manager.create_user(data["name"])

            return Response({'id': user.id}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class TokenView(APIView):
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
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            data = json.loads(request.body)

            manager = UserManager(data["user_name"])
            token = manager.add_token(data["token_name"], data["queues"])

            return Response({'token': token.value})
        except Exception as e:
            print(e)
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
