from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from .services.managers.UserManager import UserManager
import json

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
        return Response({"message": f"Hello {user.rb_username}, your service response is here!"})
    
    def post(self, request):
        try:
            data = json.loads(request.body)

            manager = UserManager(data["user_id"])
            token = manager.add_token(data["name"], data["queues"])

            return Response({'token': token.value})
        except Exception as e:
            print(e)
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


