from django.db import models
from django.contrib.auth.models import User

class Kart(models.Model):
    type = models.CharField(max_length=50)
    hourly_cost = models.PositiveSmallIntegerField()
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    def get_cost(self):
        return self.hourly_cost


class Balance(models.Model):
    balance = models.FloatField(default=0.0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def get_balance(self):
        return self.balance


class Booking(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kart = models.ForeignKey(Kart, on_delete=models.CASCADE)

    def get_lenght(self):
        return (self.end_time - self.start_time).total_seconds()/3600
