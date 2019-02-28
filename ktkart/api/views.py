from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import status, APIView

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from rest_framework_jwt.settings import api_settings

from validate_email import validate_email
from datetime import datetime, timedelta
from random import random
from .utils import distance

from django.db.models import Q, Sum
from .models import Kart, Balance, Booking
from .serializers import KartSerializer, BalanceSerializer, BookingSerializer, TokenSerializer

# Get the JWT settings
jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class RegisterView(APIView):
    """
    POST auth/register/
    Create a new user from email and password
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        if not validate_email(email):
            return Response(data="This email is not a valid one.", status=status.HTTP_401_UNAUTHORIZED)
        # Check if email not already taken
        user = User.objects.filter(email=email)
        if user:
            return Response(data="This email is already used by someone.", status=status.HTTP_401_UNAUTHORIZED)
        else:
            new_user = User.objects.create_user(email=email, password=password, username=email)
            Balance.objects.create(balance=5, user=new_user)
            return Response(data="Your account was successfully created.", status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST auth/login/
    Authenticate user with email and password, return token if sucess
    """

    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            serializer = TokenSerializer(data={
                "token": jwt_encode_handler(
                    jwt_payload_handler(user)
                )})
            serializer.is_valid()
            return Response(serializer.data)
        return Response(data="Authentication failed.", status=status.HTTP_401_UNAUTHORIZED)


class GetBalanceView(APIView):
    """
    GET balance/get
    Return the balance of the authenticated user that makes the request
    """

    permission_classes = (permissions.IsAuthenticated,)
    queryset = Balance.objects.all()

    def get(self, request):
        user = request.user
        balance = Balance.objects.get(user=user)
        return Response(BalanceSerializer(balance).data)


class UpdateBalanceView(APIView):
    """
    PUT balance/update
    Admin user can update the balance of a common user
    """

    # only admin user can use this route to update balance
    permission_classes = (permissions.IsAdminUser,)
    queryset = Balance.objects.all()

    def put(self, request):
        try:
            email = request.data.get("email", "")
            new_balance = request.data.get("new_balance", "")
            if new_balance >= 0:
                user = User.objects.get(email=email)
                updated_balance = Balance.objects.get(user=user)
                updated_balance.balance = new_balance
                updated_balance.save()
                return Response(BalanceSerializer(updated_balance).data)
            return Response(data="Balance must be positive.", status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response(data="User with provided email not found.", status=status.HTTP_404_NOT_FOUND)



class GetAvailableKartsView(APIView):
    """
    POST available_karts
    Given start date and end date, returns available karts during the period
    No restriction on the period given
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            start = datetime.strptime(request.data.get("start", ""), '%Y-%m-%d %H:%M:%S.%f')
            end = datetime.strptime(request.data.get("end", ""), '%Y-%m-%d %H:%M:%S.%f')
            overlaping_bookings = Booking.objects.filter(Q(end_time__gte=start) & Q(start_time__lte=end)).values('kart').distinct()
            available_karts = Kart.objects.exclude(id__in=overlaping_bookings)
            return Response(KartSerializer(available_karts, many=True).data)
        except ValueError:
            return Response("Datetime format not respected. Must be %Y-%m-%d %H:%M:%S.%f")


class BookingView(APIView):
    """
    GET booking/
    POST booking/
    PUT booking/
    DELETE booking/
    """

    permission_classes = (permissions.IsAuthenticated,)
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get(self, request):
        user = request.user
        bookings = Booking.objects.filter(user=user)
        return Response(BookingSerializer(bookings, many=True).data)

    def post(self, request):
        try:
            start = datetime.strptime(request.data.get("start", ""), '%Y-%m-%d %H:%M:%S.%f')
            end = datetime.strptime(request.data.get("end", ""), '%Y-%m-%d %H:%M:%S.%f')
            booking_hour_length = (end-start).total_seconds()/3600
            kart_id = request.data.get("kart_id", "")
            user = request.user

            # you can only book a kart "in the future"
            if start < datetime.now():
                return Response(data="Booking before present time is not possible.", status=status.HTTP_401_UNAUTHORIZED)

            # booking must last more than one hour
            elif booking_hour_length < 1:
                return Response(data="Booking must be 1hr minimum.", status=status.HTTP_401_UNAUTHORIZED)

            # check if kart is available
            kart_overlaping_bookings = Booking.objects.filter(Q(end_time__gte=start) & Q(start_time__lte=end) & Q(kart__id=kart_id))
            if kart_overlaping_bookings:
                return Response(data="This kart is not available during this period.", status=status.HTTP_401_UNAUTHORIZED)

            # check if user's balance is enough
            balance = Balance.objects.get(user=user)
            kart = Kart.objects.get(id=kart_id)
            user_balance = balance.get_balance()
            to_pay = booking_hour_length * kart.get_cost()
            to_pay = round(to_pay, 2)
            if user_balance < to_pay:
                return Response(data="Not enough balance to book.", status=status.HTTP_401_UNAUTHORIZED)
            # proceed booking
            balance.balance -= to_pay
            balance.save()
            new_booking = Booking.objects.create(
                start_time = start,
                end_time = end,
                kart = kart,
                user = user
            )
            return Response({
                "reservation": BookingSerializer(new_booking).data,
                "price": '$'+str(to_pay),
                "new_balance": BalanceSerializer(balance).data
            })
        except Kart.DoesNotExist:
            return Response("No such kart id", status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response("Datetime format not respected. Must be %Y-%m-%d %H:%M:%S.%f")



    def put(self, request):
        try:
            booking_id = request.data.get("booking_id", "")
            new_start = datetime.strptime(request.data.get("start", ""), '%Y-%m-%d %H:%M:%S.%f')
            new_end = datetime.strptime(request.data.get("end", ""), '%Y-%m-%d %H:%M:%S.%f')
            new_length = (new_end - new_start).total_seconds()/3600
            user = request.user
            booking = Booking.objects.get(id=booking_id, user=user)
            now = datetime.now()

            # booking is passed
            if now > booking.end_time:
                return Response(data="Cannot update a booking from the past.", status=status.HTTP_401_UNAUTHORIZED)

            # booking has not started queryset
            elif now < booking.start_time:
                if new_start < now:
                    return Response(data="New start date is past, update impossible.", status=status.HTTP_401_UNAUTHORIZED)
                elif new_length < 1:
                    return Response(data="Booking must be at least 1hr.", status=status.HTTP_401_UNAUTHORIZED)

                # check if kart is available during new period
                kart_id = booking.kart.id
                kart_overlaping_bookings = Booking.objects.filter(
                        Q(end_time__gte=new_start) & Q(start_time__lte=new_end) & Q(kart__id=kart_id)
                                                            ).exclude(id=booking_id)
                if kart_overlaping_bookings:
                    return Response(data="The kart is not available during this new period.", status=status.HTTP_401_UNAUTHORIZED)

                # check if user balance is sufficient
                balance = Balance.objects.get(user=user)
                hour_cost = booking.kart.get_cost()
                to_pay = (new_length - booking.get_lenght()) * hour_cost # can be negative if new period shorter, user is refunded
                to_pay = round(to_pay, 2)
                if balance.get_balance() < to_pay:
                    return Response(data="Balance is not sufficient for this new booking.", status=status.HTTP_401_UNAUTHORIZED)

                # else, we can update the booking along with the user's balance
                booking.start_time = new_start
                booking.end_time = new_end
                balance.balance -= to_pay
                booking.save()
                balance.save()
                return Response({
                    "reservation": BookingSerializer(booking).data,
                    "payment": '$'+str(to_pay),
                    "new_balance": BalanceSerializer(balance).data
                })

            # update during the booking period, in this case we do no update the start_time
            else:
                # trying to set new end in the past
                if new_end < now:
                    return Response(data="End date not valid for update, date is past.", status=status.HTTP_401_UNAUTHORIZED)

                # else, we take from balance if new period is longer, of refund if shorter
                # if new period is shorter than 1hr, do not refund the hour
                balance = Balance.objects.get(user=user)
                hour_cost = booking.kart.get_cost()
                new_length = max(1, (new_end - booking.start_time).total_seconds/3600) # do not refund the first hour
                to_pay = (new_length - booking.get_lenght()) * hour_cost
                to_pay = round(to_pay, 2)
                if balance.get_balance() < to_pay:
                    return Response(data="Balance is not sufficient for this new booking.", status=status.HTTP_401_UNAUTHORIZED)

                # else, we can update the booking along with the user's balance
                booking.end_time = new_end
                balance.balance -= to_pay
                booking.save()
                balance.save()
                return Response({
                    "reservation": BookingSerializer(booking).data,
                    "payment": '$'+str(to_pay),
                    "new_balance": BalanceSerializer(balance).data
                })
        except Booking.DoesNotExist:
            return Response(data="Booking was not found.", status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response("Datetime format not respected. Must be %Y-%m-%d %H:%M:%S.%f")

    def delete(self, request):
        try:
            booking_id = request.data.get("booking_id", "")
            user = request.user
            booking = Booking.objects.get(id=booking_id, user=user)
            if datetime.now() > booking.start_time:
                return Response(data="Can only delete upcoming bookings.", status=status.HTTP_401_UNAUTHORIZED)
            duration = booking.get_lenght()
            hour_price = booking.kart.get_cost()
            refund = round(duration * hour_price, 2)
            balance = Balance.objects.get(user=user)
            balance.balance += refund
            balance.save()
            booking.delete()
            return Response(data="Booking deleted, accout was refunded by $+{}.".format(refund), status=status.HTTP_204_NO_CONTENT)
        except Booking.DoesNotExist:
            return Response(data="Booking was not found.", status=status.HTTP_404_NOT_FOUND)


class GetNearKartsView(APIView):
    """
    POST near_karts/
    Will return the list of karts that are available for the next hour, ordered by distance
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user_lat = request.data.get("lat", "")
        user_lng = request.data.get("lng", "")
        start = datetime.now()
        end = start + timedelta(seconds=3600)
        overlaping_bookings = Booking.objects.filter(Q(end_time__gte=start) & Q(start_time__lte=end)).values('kart').distinct()
        available_karts = Kart.objects.exclude(id__in=overlaping_bookings)
        sorted_available_karts = sorted(available_karts, key=lambda x:distance(user_lng, user_lat, x.longitude, x.latitude))
        return Response(KartSerializer(sorted_available_karts, many=True).data)


class MultipleBookingView(APIView):
    """
    POST multiple_booking/
    Will allow user to create multiple bookings in one request
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        start = datetime.strptime(request.data.get("start", ""), '%Y-%m-%d %H:%M:%S.%f')
        end = datetime.strptime(request.data.get("end", ""), '%Y-%m-%d %H:%M:%S.%f')
        booking_hour_length = (end-start).total_seconds()/3600
        kart_ids = request.data.get("kart_ids", "")
        user = request.user

        # you can only book a kart "in the future"
        if start < datetime.now():
            return Response(data="Booking before present time is not possible.", status=status.HTTP_401_UNAUTHORIZED)

        # booking must last more than one hour
        elif booking_hour_length < 1:
            return Response(data="Booking must be 1hr minimum.", status=status.HTTP_401_UNAUTHORIZED)

        # check if kart is available
        kart_overlaping_bookings = Booking.objects.filter(Q(end_time__gte=start) & Q(start_time__lte=end) & Q(kart__id__in=kart_ids))
        if kart_overlaping_bookings:
            return Response(data={
                "message": "Some karts are not available during period",
                "not_available_karts": list(map(lambda x:x.kart.id, kart_overlaping_bookings))
            }, status=status.HTTP_401_UNAUTHORIZED)

        # check if user's balance is enough
        balance = Balance.objects.get(user=user)
        karts = Kart.objects.filter(id__in=kart_ids)
        # check if all ids given correspond to a kart
        if karts.count() < len(kart_ids):
            return Response("Provided ids are not correct")

        user_balance = balance.get_balance()
        print(karts.aggregate(Sum('hourly_cost')))
        to_pay = booking_hour_length * karts.aggregate(Sum('hourly_cost'))['hourly_cost__sum']
        to_pay = round(to_pay, 2)
        if user_balance < to_pay:
            return Response(data="Not enough balance to book.", status=status.HTTP_401_UNAUTHORIZED)
        # proceed booking
        balance.balance -= to_pay
        balance.save()
        bookings = []
        for kart in karts:
            new_booking = Booking.objects.create(
                start_time = start,
                end_time = end,
                kart = kart,
                user = user
            )
            bookings.append(BookingSerializer(new_booking).data)
        return Response({
            "reservation": bookings,
            "price": '$'+str(to_pay),
            "new_balance": BalanceSerializer(balance).data
        })

class PopulateView(APIView):
    """
    GET populate/
    Will init population of database
    """

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        all = Kart.objects.all()
        if all.count() == 0:
            for i in range(5):
                Kart.objects.create(type="Standard", hourly_cost=10, latitude=48+random(), longitude=2+random())
            for i in range(2):
                Kart.objects.create(type="Cat Cruiser", hourly_cost=15, latitude=48+random(), longitude=2+random())
            for i in range(3):
                Kart.objects.create(type="Blue Falcon", hourly_cost=25, latitude=48+random(), longitude=2+random())
            return Response('Populated')
        return Response('Was already populated')
