import json
from django.urls import reverse
from django.contrib.auth.models import User

from rest_framework.test import APITestCase, APIClient
from rest_framework.views import status
from .models import Booking, Balance, Kart
from .serializers import BookingSerializer, BalanceSerializer, KartSerializer

from datetime import datetime, timedelta

class BaseViewTest(APITestCase):
    """
    Setup all the tests. Test classes implements BaseViewTest
    """
    client = APIClient()

    def login_user(self, email="", password=""):
        url = reverse("auth-login")
        return self.client.post(
            url,
            data=json.dumps({
                "email": email,
                "password": password
            }),
            content_type="application/json"
        )

    def register_user(self, email="", password=""):
        return self.client.post(
            reverse("auth-register"),
            data=json.dumps(
                {
                    "password": password,
                    "email": email
                }
            ),
            content_type='application/json'
        )

    def login_for_auth(self, email="", password=""):
        # authenticate user to make request with a token
        response = self.client.post(
            reverse("auth-login"),
            data=json.dumps(
                {
                    'email': email,
                    'password': password
                }
            ),
            content_type='application/json'
        )
        self.token = response.data['token']
        # set the token in the header
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer ' + self.token
        )
        self.client.login(username=email, password=password)
        return self.token

    def get_balance(self):
        return self.client.get(
            reverse("balance-get"),
            content_type='application/json'
        )

    def update_balance(self, email, new_balance):
        return self.client.put(
            reverse("balance-update"),
            data=json.dumps(
                {
                    "email": email,
                    "new_balance": new_balance
                }
            ),
            content_type='application/json'
        )

    def get_available_karts(self, start, end):
        return self.client.post(
            reverse("available_karts"),
            data=json.dumps(
                {
                    "start": start,
                    "end": end
                }
            ),
            content_type='application/json'
        )

    def get_booking(self):
        return self.client.get(
            reverse('booking'),
            content_type='application/json'
        )

    def post_booking(self, start, end, kart_id):
        return self.client.post(
            reverse("booking"),
            data=json.dumps(
                {
                    "start": start,
                    "end": end,
                    "kart_id": kart_id
                }
            ),
            content_type='application/json'
        )

    def update_booking(self, start, end, booking_id):
        return self.client.put(
            reverse("booking"),
            data=json.dumps(
                {
                    "start": start,
                    "end": end,
                    "booking_id": booking_id
                }
            ),
            content_type='application/json'
        )

    def delete_booking(self, booking_id):
        return self.client.delete(
            reverse("booking"),
            data=json.dumps(
                {
                    "booking_id": booking_id
                }
            ),
            content_type='application/json'
        )

    def setUp(self):
        self.user = User.objects.create_superuser(
            email="test@mail.com",
            password="testing",
            username="test@mail.com"
        )
        self.balance = Balance.objects.create(balance=100, user=self.user)
        for i in range (5):
            Kart.objects.create(type="Standard", hourly_cost=10, latitude=48, longitude=2)
        for i in range (2):
            Kart.objects.create(type="Blue Falcon", hourly_cost=15, latitude=48.5, longitude=2.5)
        for i in range (3):
            Kart.objects.create(type="Cat Cruiser", hourly_cost=25, latitude=49, longitude=3)


class RegisterTest(BaseViewTest):
    """
    Tests for auth/register/ endpoint
    """
    def test_register_user(self):
        """ register should succeed """
        response = self.register_user("new_user@mail.com", "password")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        """ register should fail """
        response = self.register_user("NOTVALIDEMAIL", "password") # invalid email
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.register_user("new_user@mail.com", "password") # email already taken
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginTest(BaseViewTest):
    """
    Tests for auth/login/ endpoint
    """
    def test_login_user(self):
        """ login should succeed """
        response = self.login_user("test@mail.com", "testing")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        """ login should fail """
        response = self.login_user("noregister@mail.com", "password") # invalid email
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        """ test register + login """
        response = self.register_user("new_user@mail.com", "password")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.login_user("new_user@mail.com", "password")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetBalanceTest(BaseViewTest):
    """
    Tests for balance/get/ endpoint
    """
    def test_get_balance(self):
        """ get balance without login, should fail """
        response = self.get_balance()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        """ with login, should work """
        self.login_for_auth("test@mail.com", "testing")
        response = self.get_balance()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = BalanceSerializer(Balance.objects.get(user=self.user))
        self.assertEqual(expected.data, response.data)

        """ test if new user has $5 balance """
        self.register_user("new_user@mail.com", "password")
        self.login_for_auth("new_user@mail.com", "password")
        response = self.get_balance()
        self.assertEqual(response.data['balance'], 5)


class UpdateBalanceTest(BaseViewTest):
    """
    Tests for balance/update/ endpoint
    """
    def test_update_balance(self):
        """ superuser update balance should work """
        self.login_for_auth("test@mail.com", "testing")
        response = self.update_balance("test@mail.com", 1000)
        expected = BalanceSerializer(Balance.objects.get(user=self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(expected.data, response.data)

        """ normal user cannot update balance """
        self.register_user("new_user@mail.com", "password")
        self.login_for_auth("new_user@mail.com", "password")
        response = self.update_balance("new_user@mail.com", 1000000)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        """ should return 404 if email is not a user """
        self.login_for_auth("test@mail.com", "testing")
        response = self.update_balance("NOAVALIDEMAIL", 1000)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GetAvailableKartsTest(BaseViewTest):
    """
    Tests available_karts/ endpoint
    """
    def test_get_available_karts(self):
        """ as there is no booking, should always respond with all karts... """
        self.login_for_auth("test@mail.com", "testing")
        response = self.get_available_karts('2019-02-27 10:00:00.00', '2019-02-27 11:00:00.00')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = KartSerializer(Kart.objects.all(), many=True)
        self.assertEqual(expected.data, response.data)


class BookingTest(BaseViewTest):
    """
    Tests booking/ endpoint (GET, POST, PUT, DELETE)
    """
    def test_post_booking(self):
        valid_kart_ids = list(map(lambda x:x.id, Kart.objects.all()))
        self.login_for_auth("test@mail.com", "testing")

        """ correct booking that should pass """
        start = datetime.now() + timedelta(seconds=3600)
        end = start + timedelta(seconds=3600)
        response = self.post_booking(str(start), str(end), valid_kart_ids[0])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        """ the same booking should not work """
        response = self.post_booking(str(start), str(end), valid_kart_ids[0])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        """ invalid id should return 404 """
        response = self.post_booking(str(start), str(end), 100)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        """ with other kart should work """
        response = self.post_booking(str(start), str(end), valid_kart_ids[2])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        """ booking in the past should not pass """
        start = datetime.now() - timedelta(seconds=3600)
        end = start + timedelta(seconds=3600)
        response = self.post_booking(str(start), str(end), valid_kart_ids[3])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        """ booking less than 1hr sould not pass """
        start = datetime.now() + timedelta(seconds=3600)
        end = start + timedelta(seconds=1800)
        response = self.post_booking(str(start), str(end), valid_kart_ids[3])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        """ if balance is not enough, should fail """
        self.update_balance("test@mail.com", 0)
        response = self.post_booking(str(start), str(end), valid_kart_ids[3])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_booking(self):
        valid_kart_ids = list(map(lambda x:x.id, Kart.objects.all()))
        self.login_for_auth("test@mail.com", "testing")

        """ works with nothing in the database """
        response = self.get_booking()
        expected = BookingSerializer(Booking.objects.filter(user = self.user), many=True)
        self.assertEqual(expected.data, response.data)

        """ works after posting a new booking """
        start = datetime.now() + timedelta(seconds=3600)
        end = start + timedelta(seconds=3600)
        self.post_booking(str(start), str(end), valid_kart_ids[0])
        response = self.get_booking()
        expected = BookingSerializer(Booking.objects.filter(user = self.user), many=True)
        self.assertEqual(expected.data, response.data)

    def test_update_booking(self):
        valid_kart_ids = list(map(lambda x:x.id, Kart.objects.all()))
        self.login_for_auth("test@mail.com", "testing")

        """ update a booking we have just made """
        start = datetime.now() + timedelta(seconds=3600)
        end = start + timedelta(seconds=3600)
        booking = self.post_booking(str(start), str(end), valid_kart_ids[0])
        booking_id = booking.data["reservation"]["id"]
        response = self.update_booking(str(start), str(end+timedelta(seconds=3600)), booking_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        """ try to update it so that the balance is no enough """
        response = self.update_booking(str(start), str(end+timedelta(seconds=36000000)), booking_id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_booking(self):
        valid_kart_ids = list(map(lambda x:x.id, Kart.objects.all()))
        self.login_for_auth("test@mail.com", "testing")

        """ check if we can delete a booking and if our balance is refunded """
        balance_init = Balance.objects.get(user=self.user).get_balance()
        start = datetime.now() + timedelta(seconds=3600)
        end = start + timedelta(seconds=3600)
        booking = self.post_booking(str(start), str(end), valid_kart_ids[0])
        booking_id = booking.data["reservation"]["id"]
        response = self.delete_booking(booking_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        balance_end = Balance.objects.get(user=self.user).get_balance()
        self.assertEqual(balance_init, balance_end)
