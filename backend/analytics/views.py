from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.queue_manager import RabbitAccountManager
from .services.queue_type import queue_type

# Create your views here.
class CreateAccount(APIView):
    def post(self, request):
        try:
            account_manager = RabbitAccountManager({"name": "amdor"})
            account_manager.create_account()
            account_manager.add_queue("started_session", queue_type.SINGLE_VALUE)
            #account_manager.remove_account()
            return Response("successful", status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(f"error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)