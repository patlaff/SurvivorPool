from rest_framework import serializers
from .models import User


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'display_name', 'avatar_url')
        read_only_fields = fields
