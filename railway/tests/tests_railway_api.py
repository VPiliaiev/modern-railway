from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from rest_framework import status
from django.contrib.auth import get_user_model
import tempfile
import os

from PIL import Image
from railway.models import (
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Trip
)

STATION_URL = reverse("railway:station-list")
ROUTE_URL = reverse("railway:route-list")
TRAIN_URL = reverse("railway:train-list")
TRIP_URL = reverse("railway:trip-list")
CREW_URL = reverse("railway:crew-list")
TRAIN_TYPE_URL = reverse("railway:traintype-list")
User = get_user_model()


def sample_station(**params):
    defaults = {"name": "Kyiv", "latitude": 50.45, "longitude": 30.52}
    defaults.update(params)
    return Station.objects.create(**defaults)


def sample_route(**params):
    source = params.pop("source", sample_station(name="Kyiv"))
    destination = params.pop("destination", sample_station(name="Lviv"))
    defaults = {"distance": 500}
    defaults.update(params)
    return Route.objects.create(source=source, destination=destination, **defaults)


def sample_train_type(**params):
    defaults = {"name": "Intercity+"}
    defaults.update(params)
    return TrainType.objects.create(**defaults)


def sample_train(**params):
    train_type = params.pop("train_type", sample_train_type())
    defaults = {
        "name": "Hyundai",
        "cargo_num": 9,
        "places_in_cargo": 50,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


def sample_crew(**params):
    defaults = {"first_name": "Bob", "last_name": "Lasso"}
    defaults.update(params)
    return Crew.objects.create(**defaults)


def sample_trip(**params):
    route = params.pop("route", sample_route())
    train = params.pop("train", sample_train())
    defaults = {
        "route": route,
        "train": train,
        "departure_time": timezone.now() + timedelta(hours=2),
        "arrival_time": timezone.now() + timedelta(hours=6),
    }
    defaults.update(params)
    trip = Trip.objects.create(**defaults)
    trip.crew.add(sample_crew())
    return trip


def image_upload_url(train_id):
    return reverse("railway:train-upload-image", args=[train_id])


def detail_url(train_id):
    return reverse("railway:train-detail", args=[train_id])


class UnauthenticatedRailwayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRailwayApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="Test12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_trip(self):
        sample_trip()
        sample_trip()

        res = self.client.get(TRIP_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)
        self.assertIn("results", res.data)

        first_trip = res.data["results"][0]

        for key in ["id", "source", "destination", "departure_time", "arrival_time", "train_name", "train_type",
                    "total_seats", "tickets_available"]:
            self.assertIn(key, first_trip)

        expected_total = 9 * 50
        self.assertEqual(first_trip["total_seats"], expected_total)

    def test_filter_trip_by_source(self):
        kyiv_trip = sample_trip(route=sample_route(
            source=sample_station(name="Kyiv"), destination=sample_station(name="Lviv")
        ))
        sample_trip(route=sample_route(
            source=sample_station(name="Odesa"), destination=sample_station(name="Kharkiv")
        ))

        res = self.client.get(TRIP_URL, {"source": "Kyiv"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], kyiv_trip.id)

    def test_filter_trip_by_destination(self):
        lviv_trip = sample_trip(route=sample_route(
            source=sample_station(name="Kyiv"), destination=sample_station(name="Lviv")
        ))
        sample_trip(route=sample_route(
            source=sample_station(name="Kharkiv"), destination=sample_station(name="Odesa")
        ))

        res = self.client.get(TRIP_URL, {"destination": "Lviv"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], lviv_trip.id)

    def test_filter_trips_by_date(self):
        base_time = timezone.now()
        today_trip = sample_trip(
            departure_time=base_time + timedelta(hours=2),
            arrival_time=base_time + timedelta(hours=5),
        )
        sample_trip(
            departure_time=base_time + timedelta(days=1, hours=2),
            arrival_time=base_time + timedelta(days=1, hours=5),
        )
        today_str = base_time.date().isoformat()

        res = self.client.get(TRIP_URL, {"date": today_str})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], today_trip.id)

    def test_list_stations(self):
        sample_station(name="Kyiv")
        sample_station(name="Lviv")

        res = self.client.get(STATION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

    def test_list_routes(self):
        sample_route()
        sample_route(source=sample_station(name="Odesa"), destination=sample_station(name="Kharkiv"))

        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

    def test_list_trains(self):
        sample_train(name="Hyundai")
        sample_train(name="Skoda")

        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

    def test_retrieve_trip_detail(self):
        trip = sample_trip()

        url = reverse("railway:trip-detail", args=[trip.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], trip.id)
        self.assertIn("crew", res.data)

    def test_user_cannot_create_trip(self):
        payload = {
            "route": sample_route().id,
            "train": sample_train().id,
            "departure_time": timezone.now() + timedelta(hours=3),
            "arrival_time": timezone.now() + timedelta(hours=6),
        }

        res = self.client.post(TRIP_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_update_trip(self):
        trip = sample_trip()
        payload = {"departure_time": timezone.now() + timedelta(hours=10)}

        url = reverse("railway:trip-detail", args=[trip.id])
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_trip_invalid_date(self):
        sample_trip()
        res = self.client.get(TRIP_URL, {"date": "invalid-date"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data["count"], 1)

    def test_user_cannot_delete_trip(self):
        trip = sample_trip()
        url = reverse("railway:trip-detail", args=[trip.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_train_detail(self):
        train = sample_train()
        url = reverse("railway:train-detail", args=[train.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], train.id)
        self.assertIn("train_type", res.data)

    def test_retrieve_station_detail(self):
        station = sample_station(name="Kyiv")
        url = reverse("railway:station-detail", args=[station.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Kyiv")

    def test_retrieve_route_detail(self):
        route = sample_route()
        url = reverse("railway:route-detail", args=[route.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], route.id)
        self.assertIn("source", res.data)
        self.assertIn("destination", res.data)

    def test_filter_trip_no_results(self):
        sample_trip(route=sample_route(source=sample_station(name="Kyiv")))
        res = self.client.get(TRIP_URL, {"source": "London"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)


class AdminRailwayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.station1 = Station.objects.create(name="Kyiv", latitude=50.45, longitude=30.52)
        self.station2 = Station.objects.create(name="Lviv", latitude=49.84, longitude=24.03)
        self.route = Route.objects.create(
            source=self.station1,
            destination=self.station2,
            distance=540
        )
        self.train_type = TrainType.objects.create(name="Intercity+")
        self.train = Train.objects.create(
            name="Hyundai",
            cargo_num=5,
            places_in_cargo=20,
            train_type=self.train_type
        )

    def test_create_train_type(self):
        payload = {"name": "Regional"}
        res = self.client.post(TRAIN_TYPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TrainType.objects.filter(name="Regional").exists())

    def test_create_train(self):
        payload = {
            "name": "R777",
            "cargo_num": 3,
            "places_in_cargo": 30,
            "train_type": self.train_type.id,
        }
        res = self.client.post(TRAIN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        train = Train.objects.get(id=res.data["id"])
        self.assertEqual(train.name, payload["name"])
        self.assertEqual(train.train_type, self.train_type)
        self.assertEqual(train.capacity, 90)

    def test_create_crew(self):
        payload = {"first_name": "Oleh", "last_name": "Shevchenko"}
        res = self.client.post(CREW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        crew = Crew.objects.get(id=res.data["id"])
        self.assertEqual(crew.full_name, "Oleh Shevchenko")

    def test_create_trip(self):
        payload = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_time": datetime.now().isoformat(),
            "arrival_time": (datetime.now() + timedelta(hours=5)).isoformat(),
        }
        res = self.client.post(TRIP_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        trip = Trip.objects.get(id=res.data["id"])
        self.assertEqual(trip.route, self.route)
        self.assertEqual(trip.train, self.train)

    def test_create_trip_invalid_times(self):
        now = datetime.now()
        payload = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_time": now.isoformat(),
            "arrival_time": now.isoformat(),
        }
        res = self.client.post(TRIP_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class TrainImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@railway.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.train_type = TrainType.objects.create(name="Intercity")
        self.train = Train.objects.create(
            name="Tarpan",
            cargo_num=3,
            places_in_cargo=30,
            train_type=self.train_type,
        )

    def tearDown(self):
        if self.train.image:
            self.train.image.delete()

    def test_upload_image_to_train(self):
        url = reverse("railway:train-upload-image", args=[self.train.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.train.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.train.image.path))

    def test_upload_image_bad_request(self):
        url = reverse("railway:train-upload-image", args=[self.train.id])
        res = self.client.post(url, {"image": "not an image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_shown_on_train_detail(self):
        url = reverse("railway:train-upload-image", args=[self.train.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(reverse("railway:train-detail", args=[self.train.id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)

    def test_image_url_shown_on_train_list(self):
        url = reverse("railway:train-upload-image", args=[self.train.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(reverse("railway:train-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data["results"][0].keys())
