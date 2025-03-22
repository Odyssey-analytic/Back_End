from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from .services.managers.UserManager import UserManager
from .models import Token
import json
import random

# Create your views here.
class UserView(APIView):
    def post(self, request):
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
            return Response({
                "rb_username": user.rb_username,
                "rb_password": user.rb_password,
                "vhost_name": token_obj.VHOST_name,
                "id": random.randint(0, 100000)
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


