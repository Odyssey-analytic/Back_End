from rest_framework import serializers
from .models import User

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name']
    