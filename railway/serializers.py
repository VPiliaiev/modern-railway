from django.db import transaction
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


class StationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name")


class StationRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    source = StationSerializer(read_only=True)
    destination = StationSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]


class RouteListSerializer(serializers.ModelSerializer):
    source = serializers.StringRelatedField(read_only=True)
    destination = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Route
        fields = ["id", "source", "destination", "distance"]


class RouteRetrieveSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type",
            "capacity",
        )


class TrainListSerializer(serializers.ModelSerializer):
    train_type = serializers.CharField(source="train_type.name", read_only=True)

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type",
            "capacity",
            "image",
        )


class TrainRetrieveSerializer(serializers.ModelSerializer):
    train_type = TrainTypeSerializer(read_only=True)

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type",
            "capacity",
            "image",
        )


class TrainImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "image")


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ("id", "route", "train", "departure_time", "arrival_time")

    def validate(self, attrs):
        Trip.validate_times(
            attrs["departure_time"],
            attrs["arrival_time"],
            serializers.ValidationError
        )
        return attrs


class TripListSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="route.source.name", read_only=True)
    destination = serializers.CharField(source="route.destination.name", read_only=True)
    train_name = serializers.CharField(source="train.name", read_only=True)
    train_type = serializers.CharField(source="train.train_type.name", read_only=True)
    total_seats = serializers.IntegerField(read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Trip
        fields = (
            "id",
            "source",
            "destination",
            "departure_time",
            "arrival_time",
            "train_name",
            "train_type",
            "total_seats",
            "tickets_available",
        )


class TripRetrieveSerializer(serializers.ModelSerializer):
    train = serializers.CharField(source="train.name", read_only=True)
    train_type = serializers.CharField(source="train.train_type.name", read_only=True)
    total_seats = serializers.IntegerField(source="train.capacity", read_only=True)
    taken_seats = serializers.SerializerMethodField()
    crew = serializers.SerializerMethodField()
    source = serializers.CharField(source="route.source.name", read_only=True)
    destination = serializers.CharField(source="route.destination.name", read_only=True)

    class Meta:
        model = Trip
        fields = (
            "id",
            "source",
            "destination",
            "departure_time",
            "arrival_time",
            "train",
            "train_type",
            "total_seats",
            "crew",
            "taken_seats",
        )

    def get_crew(self, obj):
        return [
            crew_item.full_name for crew_item in getattr(obj, "prefetched_crew", [])
        ]

    def get_taken_seats(self, obj):
        tickets = getattr(obj, "prefetched_tickets", None)
        if tickets is not None:
            return [{"cargo": ticket.cargo, "seat": ticket.seat} for ticket in tickets]
        return list(obj.tickets.values("cargo", "seat"))


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        trip = attrs.get("trip")

        if not trip:
            return attrs

        train = trip.train

        Ticket.validate_cargo(attrs["cargo"], train, serializers.ValidationError)
        Ticket.validate_seat(attrs["seat"], train, serializers.ValidationError)

        if Ticket.objects.filter(
                trip=trip, cargo=attrs["cargo"], seat=attrs["seat"]
        ).exists():
            raise serializers.ValidationError(
                {
                    "seat": f"Seat {attrs['seat']} in cargo "
                            f"{attrs['cargo']} is already booked for this trip."
                }
            )

        return attrs

    class Meta:
        model = Ticket
        fields = ("id", "cargo", "seat", "trip")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class TicketListSerializer(TicketSerializer):
    trip = TripListSerializer(read_only=True)


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(read_only=True, many=True)
