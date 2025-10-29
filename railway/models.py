from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint

from modern_railway import settings


class Station(models.Model):
    name = models.CharField(max_length=64)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="departures"
    )
    destination = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="arrivals"
    )
    distance = models.IntegerField()

    def __str__(self):
        return f"{self.source} - {self.destination}"


class Crew(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)

    def __str__(self):
        return self.first_name + " " + self.last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Trip(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    train = models.ForeignKey("Train", on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField("Crew", related_name="trips")

    def __str__(self):
        return f"{self.route} ({self.departure_time:%Y-%m-%d %H:%M})"


class TrainType(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=64)
    cargo_num = models.IntegerField()
    places_in_cargo = models.IntegerField()
    train_type = models.ForeignKey(TrainType, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.train_type})"

    @property
    def capacity(self):
        return self.cargo_num * self.places_in_cargo


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at}"


class Ticket(models.Model):
    cargo = models.IntegerField()
    seat = models.IntegerField()
    trip = models.ForeignKey(
        "Trip",
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["seat", "trip"],
                name="unique_ticket_seat_trip"
            )
        ]

    def __str__(self):
        return f"{self.trip} — seat {self.seat}"

    def clean(self):
        max_seats = self.trip.train.capacity

        if not (1 <= self.seat <= max_seats):
            raise ValidationError({
                "seat": f"Seat must be in range [1, {max_seats}]"
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
