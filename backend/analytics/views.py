from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.queue_manager import RabbitAccountManager


# Create your views here.
class CreateAccount(APIView):
    def post(self, request):
        account_manager = RabbitAccountManager()
        account_manager.create_account({"name": "amdor2"})
        return Response("salam", status=status.HTTP_400_BAD_REQUEST)