# KART API

## Getting started

To run the Django server and the MySQL databases

```
docker-compose build
docker-compose up
```

You can reach the API at http://localhost:8000/.

If you want to create a superuser in order to access the Django administation page and manage the database:

```
docker-compose run django python manage.py createsuperuser
```

I did not find a proper way to initialize the database with the karts, add them to the database by making a GET request to http://localhost:8000/api/populate/.

## Database

The MySQL database is composed of four tables:

#### User table

This model uses Django user model. Note that the username and the email filed both store the user's email.

```
{
    "username": "...",
    "email": "...",
    "password": "..."
}
```

#### Balance table

Stores the balance of the user.

```
{
    "balance": FloatField,
    "user": USER_FOREIGN_KEY
}
```

#### Kart table

Stores our 10 karts, along with their position.

```
{
    "type": CharField,
    "hourly_cost": PositiveSmallIntegerField,
    "latitude": FloatField,
    "longitude": FloatField
}
```

#### Booking table

Links a kart with a user via a booking.

```
{
    "start_time": DateTimeField,
    "end_time": DateTimeField,
    "user": USER_FOREIGN_KEY,
    "kart": KART_FOREIGN_KEY
}
```

## API routes

Here is how the different routes work:

#### Create a new user with his email and password:

- endpoint: http://localhost:8000/api/auth/register/
- HTTP method: POST
- Authorization: AllowAny
- Body schema: `{ "email": ..., "password": ... }`

If the email format is correct and is not already used, it will create a new user, along with a new balance with $5.

#### Authenticate a user with his email and password:

- endpoint: http://localhost:8000/api/auth/login/
- HTTP method: POST
- Authorization: AllowAny
- Body schema: `{ "email": ..., "password": ... }`

If the email and the password are correct, the Response will contain the JWToken needed for the other routes:

```
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImVtYWlsQGVtYWlsLmZyIiwiZXhwIjoxNTUzODc2MjY5LCJlbWFpbCI6ImVtYWlsQGVtYWlsLmZyIn0.iBvZUF1E03U7LjKclUacst_meiSdRga4f75yOcjm0uY"
}
```

You must the put this token in the Authorization header, with type Bearer Token.

#### Retrieve the balance of the user:

- endpoint: http://localhost:8000/api/balance/get/
- HTTP method: PUT
- Authorization: IsAuthenticated
- Body schema: .

You must the put this token in the Authorization header, with type Bearer Token.

#### Retrieve the balance of the user:

- endpoint: http://localhost:8000/api/balance/update/
- HTTP method: GET
- Authorization: IsAdminUser
- Body schema: `{ "email": ..., "new_balance": ... }`

One user cannot modify his own balance, this can only be done by a staff user. This is why must have the email of the account to update, since it will not be done by the user itself.

#### Search all available Karts within a period:

- endpoint: http://localhost:8000/api/available_karts/
- HTTP method: POST
- Authorization: IsAuthenticated
- Body schema: `{"start": ..., "end": ...}`

The start and and field must be a datetime string formated: `"year-month-day hour:min:sec.milisec"`, for instance `"2019-02-29 10:15:00.00"`

#### Retrieve all user’s booking:

- endpoint: http://localhost:8000/api/booking/
- HTTP method: GET
- Authorization: IsAuthenticated
- Body schema: .

#### Create a new booking:

- endpoint: http://localhost:8000/api/booking/
- HTTP method: POST
- Authorization: IsAuthenticated
- Body schema: `{"start": ..., "end": ..., kart_id": ...}`

The start and and field must be a datetime string formated: `"year-month-day hour:min:sec.milisec"`, for instance `"2019-02-29 10:15:00.00"`

So that the request can be accepted, the following rules must be respected:
- booking must start after present time
- booking must be more than one hour
- the kart must be available during this period
- the user balance must be sufficient for this booking

#### Update the period of a user’s booking:

- endpoint: http://localhost:8000/api/booking/
- HTTP method: PUT
- Authorization: IsAuthenticated
- Body schema: `{"start": ..., "end": ..., booking_id": ...}`

Here also some rules must be respected:
- You cannot modify a booking that is ended
- If the booking has still not begun, the new dates must respect the same rules than for creating a new booking. If the period is shorter, the user will be refunded, if it is longer, the user must have a sufficient balance and will be debited
- If it is during the booking, you can only modify the end date. You can make the booking longer if the kart is available until then, and if the user have the balance to pay for extra time. The user can also shorten the period as long as the new end date is still future. If the new period is shorter than one hour, the user will not be fully refunded

#### Delete a user’s booking:

- endpoint: http://localhost:8000/api/booking/
- HTTP method: DELETE
- Authorization: IsAuthenticated
- Body schema: `{"booking_id": ...}`

The request will succed only if the booking has not yet started. The user will be refunded.

#### Search available Karts around the user’s location

- endpoint: http://localhost:8000/api/near_karts/
- HTTP method: POST
- Authorization: IsAuthenticated
- Body schema: `{"lat": ..., "lng": ...}`

Will respond with the list of karts that are available for the next hour, ordered by distance to the user.

#### Multiple bookings in one request

- endpoint: http://localhost:8000/api/multiple_booking/
- HTTP method: POST
- Authorization: IsAuthenticated
- Body schema: `{"start": ..., "end": ..., kart_id": [..., ...]}`

Users give a start and end time, a list of kart ids. Multiple booking will succeed if the following are respected:
- given period is in the future and more than 1hr
- all ids provided correspond to a kart
- all karts are available during the period
- the user has enough balance to book all karts
