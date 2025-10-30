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
        return f"{self.source.name} - {self.destination.name}"


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
        ordering = ("cargo", "seat")

    def __str__(self):
        return f"{self.trip} — seat {self.seat}"

    @staticmethod
    def validate_cargo(cargo: int, train, error_to_raise):
        if not (1 <= cargo <= train.cargo_num):
            raise error_to_raise({
                "cargo": f"Cargo must be in range [1, {train.cargo_num}]"
            })

    @staticmethod
    def validate_seat(seat: int, train, error_to_raise):
        if not (1 <= seat <= train.places_in_cargo):
            raise error_to_raise({
                "seat": f"Seat must be in range [1, {train.places_in_cargo}]"
            })

    def clean(self):
        train = self.trip.train
        Ticket.validate_cargo(self.cargo, train, ValidationError)
        Ticket.validate_seat(self.seat, train, ValidationError)

        if Ticket.objects.filter(
            trip=self.trip, cargo=self.cargo, seat=self.seat
        ).exists():
            raise ValidationError({
                "seat": f"Seat {self.seat} in cargo {self.cargo} for this trip is already booked."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
