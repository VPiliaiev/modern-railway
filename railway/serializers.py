from rest_framework import serializers
from railway.models import (
    Station,
    Route,
    Crew,
    Trip,
    TrainType,
    Train,
    Order,
    Ticket
)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    source = StationSerializer(read_only=True)
    destination = StationSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    train_type = TrainTypeSerializer(read_only=True)

    class Meta:
        model = Train
        fields = ("name", "cargo_num", "places_in_cargo", "train_type", "capacity")


class TripSerializer(serializers.ModelSerializer):
    train = TrainSerializer(many=False, read_only=True)

    class Meta:
        model = Trip
        fields = (
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew"
        )


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("cargo", "seat", "trip", "order")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")
