from django.db.models import Prefetch, Count, F
from django.utils.dateparse import parse_date
from rest_framework import viewsets
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
from railway.permissions import IsAdminOrIfAuthenticatedReadOnly
from railway.serializers import (
    StationSerializer,
    RouteSerializer,
    CrewSerializer,
    TripSerializer,
    TrainTypeSerializer,
    TrainSerializer,
    OrderSerializer,
    TripListSerializer,
    TripRetrieveSerializer,
    TrainListSerializer,
    TrainRetrieveSerializer,
    StationRetrieveSerializer,
    StationListSerializer,
    RouteListSerializer,
    RouteRetrieveSerializer, OrderListSerializer,
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return StationListSerializer
        elif self.action == "retrieve":
            return StationRetrieveSerializer
        return StationSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related("source", "destination")
    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteRetrieveSerializer
        return RouteSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.select_related(
        "train", "route__source", "route__destination", "train__train_type"
    ).prefetch_related(
        Prefetch("crew", to_attr="prefetched_crew"),
        Prefetch(
            "tickets",
            queryset=Ticket.objects.only("id", "cargo", "seat"),
            to_attr="prefetched_tickets",
        ),
    )
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        elif self.action == "retrieve":
            return TripRetrieveSerializer
        return TripSerializer

    @staticmethod
    def _param_to_str(query_string):
        return [
            str_param.strip()
            for str_param in query_string.split(",")
            if str_param.strip()
        ]

    @staticmethod
    def _param_to_date(query_string):
        return parse_date(query_string)

    def get_queryset(self):
        queryset = self.queryset

        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")
        date = self.request.query_params.get("date")

        if source:
            queryset = queryset.filter(route__source__name__icontains=source.strip())
        if destination:
            queryset = queryset.filter(
                route__destination__name__icontains=destination.strip()
            )
        if date:
            date_parsed = self._param_to_date(date)
            if date_parsed:
                queryset = queryset.filter(departure_time__date=date_parsed)

        if self.action == "list":
            queryset = queryset.annotate(
                total_seats=F("train__cargo_num") * F("train__places_in_cargo"),
                tickets_count=Count("tickets"),
                tickets_available=(
                        F("train__cargo_num") * F("train__places_in_cargo")
                        - Count("tickets")
                ),
            ).order_by("departure_time")
        else:
            queryset = queryset.order_by("departure_time")

        return queryset


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.select_related("train_type")
    serializer_class = TrainSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer
        elif self.action == "retrieve":
            return TrainRetrieveSerializer
        return TrainSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects
    serializer_class = OrderSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if self.action == "list":
            trip_queryset = Trip.objects.select_related(
                "route__source",
                "route__destination",
                "train__train_type"
            )
            queryset = queryset.prefetch_related(
                Prefetch("tickets__trip", queryset=trip_queryset)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        serializer = self.serializer_class

        if self.action == "list":
            serializer = OrderListSerializer

        return serializer
