from rest_framework import serializers
from .models import Kart, Balance, Booking


class KartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kart
        fields = '__all__'


class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Balance
        fields = ("balance",)


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'


class TokenSerializer(serializers.Serializer):
    """
    This serializer serializes the token data
    """
    token = serializers.CharField(max_length=255)
